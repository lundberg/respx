import json as jsonlib
import operator
import re
from abc import ABC
from enum import Enum
from functools import reduce
from http.cookies import SimpleCookie
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Pattern as RegexPattern,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)
from unittest.mock import ANY
from urllib.parse import urljoin

import httpx

from .types import CookieTypes, HeaderTypes, QueryParamTypes, URLPatternTypes


class Lookup(Enum):
    EQUAL = "eq"
    REGEX = "regex"
    STARTS_WITH = "startswith"
    CONTAINS = "contains"
    IN = "in"


class Match:
    def __init__(self, matches: bool, **context: Any) -> None:
        self.matches = matches
        self.context = context

    def __bool__(self):
        return bool(self.matches)

    def __invert__(self):
        self.matches = not self.matches
        return self

    def __repr__(self):  # pragma: nocover
        return f"<Match {self.matches}>"


class Pattern(ABC):
    key: ClassVar[str]
    lookups: ClassVar[Tuple[Lookup, ...]] = (Lookup.EQUAL,)

    lookup: Lookup
    base: Optional["Pattern"]
    value: Any

    # Automatically register all the subclasses in this dict
    __registry: ClassVar[Dict[str, Type["Pattern"]]] = {}
    registry = MappingProxyType(__registry)

    def __init_subclass__(cls) -> None:
        if not getattr(cls, "key", None) or ABC in cls.__bases__:
            return

        if cls.key in cls.__registry:
            raise TypeError(
                "Subclasses of Pattern must define a unique key. "
                f"{cls.key!r} is already defined in {cls.__registry[cls.key]!r}"
            )

        cls.__registry[cls.key] = cls

    def __init__(self, value: Any, lookup: Optional[Lookup] = None) -> None:
        if lookup and lookup not in self.lookups:
            raise NotImplementedError(
                f"{self.key!r} pattern does not support {lookup.value!r} lookup"
            )
        self.lookup = lookup or self.lookups[0]
        self.base = None
        self.value = self.clean(value)

    def __iter__(self):
        yield self

    def __and__(self, other: "Pattern") -> "Pattern":
        return _And((self, other))

    def __or__(self, other: "Pattern") -> "Pattern":
        return _Or((self, other))

    def __invert__(self):
        return _Invert(self)

    def __repr__(self):  # pragma: nocover
        return f"<{self.__class__.__name__} {self.lookup.value} {repr(self.value)}>"

    def __hash__(self):
        return hash((self.__class__, self.lookup, self.value))

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)

    def clean(self, value: Any) -> Any:
        """
        Clean and return pattern value.
        """
        return value

    def parse(self, request: httpx.Request) -> Any:  # pragma: nocover
        """
        Parse and return request value to match with pattern value.
        """
        raise NotImplementedError()

    def strip_base(self, value: Any) -> Any:  # pragma: nocover
        return value

    def match(self, request: httpx.Request) -> Match:
        try:
            value = self.parse(request)
        except Exception:
            return Match(False)

        # Match and strip base
        if self.base:
            base_match = self.base._match(value)
            if not base_match:
                return base_match
            value = self.strip_base(value)

        return self._match(value)

    def _match(self, value: Any) -> Match:
        lookup_method = getattr(self, f"_{self.lookup.value}")
        return lookup_method(value)

    def _eq(self, value: Any) -> Match:
        return Match(value == self.value)

    def _regex(self, value: str) -> Match:
        match = self.value.search(value)
        if match is None:
            return Match(False)
        return Match(True, **match.groupdict())

    def _startswith(self, value: str) -> Match:
        return Match(value.startswith(self.value))

    def _contains(self, value: Any) -> Match:  # pragma: nocover
        raise NotImplementedError()

    def _in(self, value: Any) -> Match:
        return Match(value in self.value)


class PathPattern(Pattern):
    path: Optional[str]

    def __init__(
        self, value: Any, lookup: Optional[Lookup] = None, *, path: Optional[str] = None
    ) -> None:
        self.path = path
        super().__init__(value, lookup)


class _And(Pattern):
    value: Tuple[Pattern, Pattern]

    def __repr__(self):  # pragma: nocover
        a, b = self.value
        return f"{repr(a)} AND {repr(b)}"

    def __iter__(self):
        a, b = self.value
        yield from a
        yield from b

    def match(self, request: httpx.Request) -> Match:
        a, b = self.value
        a_match = a.match(request)
        if not a_match:
            return a_match
        b_match = b.match(request)
        if not b_match:
            return b_match
        return Match(True, **{**a_match.context, **b_match.context})


class _Or(Pattern):
    value: Tuple[Pattern, Pattern]

    def __repr__(self):  # pragma: nocover
        a, b = self.value
        return f"{repr(a)} OR {repr(b)}"

    def __iter__(self):
        a, b = self.value
        yield from a
        yield from b

    def match(self, request: httpx.Request) -> Match:
        a, b = self.value
        match = a.match(request)
        if not match:
            match = b.match(request)
        return match


class _Invert(Pattern):
    value: Pattern

    def __repr__(self):  # pragma: nocover
        return f"NOT {repr(self.value)}"

    def __iter__(self):
        yield from self.value

    def match(self, request: httpx.Request) -> Match:
        return ~self.value.match(request)


class Method(Pattern):
    key = "method"
    lookups = (Lookup.EQUAL, Lookup.IN)
    value: Union[str, Sequence[str]]

    def clean(self, value: Union[str, Sequence[str]]) -> Union[str, Sequence[str]]:
        if isinstance(value, str):
            value = value.upper()
        else:
            assert isinstance(value, Sequence)
            value = tuple(v.upper() for v in value)
        return value

    def parse(self, request: httpx.Request) -> str:
        return request.method


class MultiItemsMixin:
    lookup: Lookup
    value: Any

    def _multi_items(
        self, value: Any, *, parse_any: bool = False
    ) -> Tuple[Tuple[str, Tuple[Any, ...]], ...]:
        return tuple(
            (
                key,
                tuple(
                    ANY if parse_any and v == str(ANY) else v
                    for v in value.get_list(key)
                ),
            )
            for key in sorted(value.keys())
        )

    def __hash__(self):
        return hash((self.__class__, self.lookup, self._multi_items(self.value)))

    def _eq(self, value: Any) -> Match:
        value_items = self._multi_items(self.value, parse_any=True)
        request_items = self._multi_items(value)
        return Match(value_items == request_items)

    def _contains(self, value: Any) -> Match:
        if len(self.value.multi_items()) > len(value.multi_items()):
            return Match(False)

        value_items = self._multi_items(self.value, parse_any=True)
        request_items = self._multi_items(value)

        for item in value_items:
            if item not in request_items:
                return Match(False)

        return Match(True)


class Headers(MultiItemsMixin, Pattern):
    key = "headers"
    lookups = (Lookup.CONTAINS, Lookup.EQUAL)
    value: httpx.Headers

    def clean(self, value: HeaderTypes) -> httpx.Headers:
        return httpx.Headers(value)

    def parse(self, request: httpx.Request) -> httpx.Headers:
        return request.headers


class Cookies(Pattern):
    key = "cookies"
    lookups = (Lookup.CONTAINS, Lookup.EQUAL)
    value: Set[Tuple[str, str]]

    def __hash__(self):
        return hash((self.__class__, self.lookup, tuple(sorted(self.value))))

    def clean(self, value: CookieTypes) -> Set[Tuple[str, str]]:
        if isinstance(value, dict):
            return set(value.items())

        return set(value)

    def parse(self, request: httpx.Request) -> Set[Tuple[str, str]]:
        headers = request.headers

        cookie_header = headers.get("cookie")
        if not cookie_header:
            return set()

        cookies: SimpleCookie = SimpleCookie()
        cookies.load(rawdata=cookie_header)

        return {(cookie.key, cookie.value) for cookie in cookies.values()}

    def _contains(self, value: Set[Tuple[str, str]]) -> Match:
        return Match(bool(self.value & value))


class Scheme(Pattern):
    key = "scheme"
    lookups = (Lookup.EQUAL, Lookup.IN)
    value: Union[str, Sequence[str]]

    def clean(self, value: Union[str, Sequence[str]]) -> Union[str, Sequence[str]]:
        if isinstance(value, str):
            value = value.lower()
        else:
            assert isinstance(value, Sequence)
            value = tuple(v.lower() for v in value)
        return value

    def parse(self, request: httpx.Request) -> str:
        return request.url.scheme


class Host(Pattern):
    key = "host"
    lookups = (Lookup.EQUAL, Lookup.REGEX, Lookup.IN)
    value: Union[str, RegexPattern[str], Sequence[str]]

    def clean(
        self, value: Union[str, RegexPattern[str]]
    ) -> Union[str, RegexPattern[str]]:
        if self.lookup is Lookup.REGEX and isinstance(value, str):
            value = re.compile(value)
        return value

    def parse(self, request: httpx.Request) -> str:
        return request.url.host


class Port(Pattern):
    key = "port"
    lookups = (Lookup.EQUAL, Lookup.IN)
    value: Optional[int]

    def parse(self, request: httpx.Request) -> Optional[int]:
        scheme = request.url.scheme
        port = request.url.port
        scheme_port = get_scheme_port(scheme)
        return port or scheme_port


class Path(Pattern):
    key = "path"
    lookups = (Lookup.EQUAL, Lookup.REGEX, Lookup.STARTS_WITH, Lookup.IN)
    value: Union[str, Sequence[str], RegexPattern[str]]

    def clean(
        self, value: Union[str, RegexPattern[str]]
    ) -> Union[str, RegexPattern[str]]:
        if self.lookup in (Lookup.EQUAL, Lookup.STARTS_WITH) and isinstance(value, str):
            path = urljoin("/", value)  # Ensure leading slash
            value = httpx.URL(path).path
        elif self.lookup is Lookup.REGEX and isinstance(value, str):
            value = re.compile(value)
        return value

    def parse(self, request: httpx.Request) -> str:
        return request.url.path

    def strip_base(self, value: str) -> str:
        if self.base:
            value = value[len(self.base.value) :]
            value = "/" + value if not value.startswith("/") else value
        return value


class Params(MultiItemsMixin, Pattern):
    key = "params"
    lookups = (Lookup.CONTAINS, Lookup.EQUAL)
    value: httpx.QueryParams

    def clean(self, value: QueryParamTypes) -> httpx.QueryParams:
        return httpx.QueryParams(value)

    def parse(self, request: httpx.Request) -> httpx.QueryParams:
        query = request.url.query
        return httpx.QueryParams(query)


class URL(Pattern):
    key = "url"
    lookups = (
        Lookup.EQUAL,
        Lookup.REGEX,
        Lookup.STARTS_WITH,
    )
    value: Union[str, RegexPattern[str]]

    def clean(self, value: URLPatternTypes) -> Union[str, RegexPattern[str]]:
        url: Union[str, RegexPattern[str]]
        if self.lookup is Lookup.EQUAL and isinstance(value, (str, tuple, httpx.URL)):
            _url = httpx.URL(value)
            _url = self._ensure_path(_url)
            url = str(_url)
        elif self.lookup is Lookup.REGEX and isinstance(value, str):
            url = re.compile(value)
        elif isinstance(value, (str, RegexPattern)):
            url = value
        else:
            raise ValueError(f"Invalid url: {value!r}")
        return url

    def parse(self, request: httpx.Request) -> str:
        url = request.url
        url = self._ensure_path(url)
        return str(url)

    def _ensure_path(self, url: httpx.URL) -> httpx.URL:
        if not url._uri_reference.path:
            url = url.copy_with(path="/")
        return url


class ContentMixin:
    def parse(self, request: httpx.Request) -> Any:
        content = request.read()
        return content


class Content(ContentMixin, Pattern):
    lookups = (Lookup.EQUAL,)
    key = "content"
    value: bytes

    def clean(self, value: Union[bytes, str]) -> bytes:
        if isinstance(value, str):
            return value.encode()
        return value


class JSON(ContentMixin, PathPattern):
    lookups = (Lookup.EQUAL,)
    key = "json"
    value: str

    def clean(self, value: Union[str, List, Dict]) -> str:
        return self.hash(value)

    def parse(self, request: httpx.Request) -> str:
        content = super().parse(request)
        json = jsonlib.loads(content.decode("utf-8"))

        if self.path:
            value = json
            for bit in self.path.split("__"):
                key = int(bit) if bit.isdigit() else bit
                try:
                    value = value[key]
                except KeyError as e:
                    raise KeyError(f"{self.path!r} not in {json!r}") from e
                except IndexError as e:
                    raise IndexError(f"{self.path!r} not in {json!r}") from e
        else:
            value = json

        return self.hash(value)

    def hash(self, value: Union[str, List, Dict]) -> str:
        return jsonlib.dumps(value, sort_keys=True)


class Data(ContentMixin, Pattern):
    lookups = (Lookup.EQUAL,)
    key = "data"
    value: bytes

    def clean(self, value: Dict) -> bytes:
        request = httpx.Request("POST", "/", data=value)
        data = request.read()
        return data


def M(*patterns: Pattern, **lookups: Any) -> Optional[Pattern]:
    extras = None

    for pattern__lookup, value in lookups.items():
        # Handle url pattern
        if pattern__lookup == "url":
            extras = parse_url_patterns(value)
            continue

        # Parse pattern key and lookup
        pattern_key, __, rest = pattern__lookup.partition("__")
        path, __, lookup_name = rest.rpartition("__")
        if pattern_key not in Pattern.registry:
            raise KeyError(f"{pattern_key!r} is not a valid Pattern")

        # Get pattern class
        P = Pattern.registry[pattern_key]
        pattern: Union[Pattern, PathPattern]

        if issubclass(P, PathPattern):
            # Make path supported pattern, i.e. JSON
            try:
                lookup = Lookup(lookup_name) if lookup_name else None
            except ValueError:
                lookup = None
                path = rest
            pattern = P(value, lookup=lookup, path=path)
        else:
            # Make regular pattern
            lookup = Lookup(lookup_name) if lookup_name else None
            pattern = P(value, lookup=lookup)

        # Skip patterns with no value, exept when using equal lookup
        if not pattern.value and pattern.lookup is not Lookup.EQUAL:
            continue

        patterns += (pattern,)

    # Combine and merge patterns
    combined_pattern = combine(patterns)
    if extras:
        combined_pattern = merge_patterns(combined_pattern, **extras)

    return combined_pattern


def get_scheme_port(scheme: Optional[str]) -> Optional[int]:
    return {"http": 80, "https": 443}.get(scheme or "")


def combine(
    patterns: Sequence[Pattern], op: Callable = operator.and_
) -> Optional[Pattern]:
    patterns = tuple(filter(None, patterns))
    if not patterns:
        return None
    return reduce(op, patterns)


def parse_url_patterns(
    url: Optional[URLPatternTypes], exact: bool = True
) -> Dict[str, Pattern]:
    bases: Dict[str, Pattern] = {}
    if not url or url == "all":
        return bases

    if isinstance(url, RegexPattern):
        return {"url": URL(url, lookup=Lookup.REGEX)}

    url = httpx.URL(url)
    scheme_port = get_scheme_port(url.scheme)

    if url.scheme and url.scheme != "all":
        bases[Scheme.key] = Scheme(url.scheme)
    if url.host:
        # NOTE: Host regex patterns borrowed from HTTPX source to support proxy format
        if url.host.startswith("*."):
            domain = re.escape(url.host[2:])
            regex = re.compile(f"^.+\\.{domain}$")
            bases[Host.key] = Host(regex, lookup=Lookup.REGEX)
        elif url.host.startswith("*"):
            domain = re.escape(url.host[1:])
            regex = re.compile(f"^(.+\\.)?{domain}$")
            bases[Host.key] = Host(regex, lookup=Lookup.REGEX)
        else:
            bases[Host.key] = Host(url.host)
    if url.port and url.port != scheme_port:
        bases[Port.key] = Port(url.port)
    if url._uri_reference.path:  # URL.path always returns "/"
        lookup = Lookup.EQUAL if exact else Lookup.STARTS_WITH
        bases[Path.key] = Path(url.path, lookup=lookup)
    if url.query:
        lookup = Lookup.EQUAL if exact else Lookup.CONTAINS
        bases[Params.key] = Params(url.query, lookup=lookup)

    return bases


def merge_patterns(pattern: Optional[Pattern], **bases: Pattern) -> Optional[Pattern]:
    if not bases:
        return pattern

    if pattern:
        # Flatten pattern
        patterns = list(iter(pattern))

        if "host" in (_pattern.key for _pattern in patterns):
            # Pattern is "absolute", skip merging
            bases = {}
        else:
            # Traverse pattern and set related base
            for _pattern in patterns:
                base = bases.pop(_pattern.key, None)
                # Skip "exact" base + don't overwrite existing base
                if _pattern.base or base and base.lookup is Lookup.EQUAL:
                    continue
                _pattern.base = base

    if bases:
        # Combine left over base patterns with pattern
        base_pattern = combine(list(bases.values()))
        if pattern and base_pattern:
            pattern = base_pattern & pattern
        else:
            pattern = base_pattern

    return pattern
