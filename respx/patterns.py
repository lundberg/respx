import operator
import re
from enum import Enum
from functools import reduce
from http.cookies import SimpleCookie
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Pattern as RegexPattern,
    Sequence,
    Set,
    Tuple,
    Union,
)
from urllib.parse import urljoin

import httpx

from .types import (
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestTypes,
    URLPatternTypes,
)


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


class Pattern:
    lookups: Tuple[Lookup, ...] = (Lookup.EQUAL,)
    lookup: Lookup
    key: str
    base: Optional["Pattern"]
    value: Any

    def __init__(self, value: Any, lookup: Optional[Lookup] = None) -> None:
        if lookup and lookup not in self.lookups:
            raise NotImplementedError(
                f"{lookup.value!r} is not a valid Lookup for {self.__class__.__name__!r}"
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

    def parse(self, request: RequestTypes) -> Any:  # pragma: nocover
        """
        Parse and return request value to match with pattern value.
        """
        raise NotImplementedError()

    def strip_base(self, value: Any) -> Any:  # pragma: nocover
        return value

    def match(self, request: RequestTypes) -> Match:
        value = self.parse(request)

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


class _And(Pattern):
    value: Tuple[Pattern, Pattern]

    def __repr__(self):  # pragma: nocover
        a, b = self.value
        return f"{repr(a)} AND {repr(b)}"

    def __iter__(self):
        a, b = self.value
        yield from a
        yield from b

    def match(self, request: RequestTypes) -> Match:
        a, b = self.value
        match1 = a.match(request)
        match2 = b.match(request)
        if match1 and match2:
            return Match(True, **{**match1.context, **match2.context})
        return Match(False)


class _Or(Pattern):
    value: Tuple[Pattern, Pattern]

    def __repr__(self):  # pragma: nocover
        a, b = self.value
        return f"{repr(a)} OR {repr(b)}"

    def __iter__(self):
        a, b = self.value
        yield from a
        yield from b

    def match(self, request: RequestTypes) -> Match:
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

    def match(self, request: RequestTypes) -> Match:
        return ~self.value.match(request)


class Method(Pattern):
    lookups = (Lookup.EQUAL, Lookup.IN)
    key = "method"
    value: Union[str, Sequence[str]]

    def clean(self, value: Union[str, Sequence[str]]) -> Union[str, Sequence[str]]:
        if isinstance(value, str):
            return value.upper()
        return value

    def parse(self, request: RequestTypes) -> str:
        if isinstance(request, httpx.Request):
            method = request.method
        else:
            _method, *_ = request
            method = _method.decode("ascii")
        return method


class MultiItemsMixin:
    lookup: Lookup
    value: Any

    def __hash__(self):
        return hash((self.__class__, self.lookup, str(self.value)))

    def _contains(self, value: Any) -> Match:
        value_list = self.value.multi_items()
        request_list = value.multi_items()

        if len(value_list) > len(request_list):
            return Match(False)

        for item in value_list:
            if item not in request_list:
                return Match(False)

        return Match(True)


class Headers(MultiItemsMixin, Pattern):
    lookups = (Lookup.CONTAINS, Lookup.EQUAL)
    key = "headers"
    value: httpx.Headers

    def clean(self, value: HeaderTypes) -> httpx.Headers:
        return httpx.Headers(value)

    def parse(self, request: RequestTypes) -> httpx.Headers:
        if isinstance(request, httpx.Request):
            headers = request.headers
        else:
            _, _, _headers, *_ = request
            headers = httpx.Headers(_headers)

        return headers


class Cookies(Pattern):
    lookups = (Lookup.CONTAINS, Lookup.EQUAL)
    key = "cookies"
    value: Set[Tuple[str, str]]

    def __hash__(self):
        return hash((self.__class__, self.lookup, tuple(sorted(self.value))))

    def clean(self, value: CookieTypes) -> Set[Tuple[str, str]]:
        if isinstance(value, dict):
            return set(value.items())

        return set(value)

    def parse(self, request: RequestTypes) -> Set[Tuple[str, str]]:
        if isinstance(request, httpx.Request):
            headers = request.headers
        else:
            _, _, _headers, *_ = request
            headers = httpx.Headers(_headers)

        cookie_header = headers.get("cookie")
        if not cookie_header:
            return set()

        cookies: SimpleCookie = SimpleCookie()
        cookies.load(rawdata=cookie_header)

        return {(cookie.key, cookie.value) for cookie in cookies.values()}

    def _contains(self, value: Set[Tuple[str, str]]) -> Match:
        return Match(bool(self.value & value))


class Scheme(Pattern):
    lookups = (Lookup.EQUAL, Lookup.IN)
    key = "scheme"
    value: Union[str, Sequence[str]]

    def clean(self, value: Union[str, Sequence[str]]) -> Union[str, Sequence[str]]:
        if isinstance(value, str):
            return value.lower()
        return value

    def parse(self, request: RequestTypes) -> str:
        if isinstance(request, httpx.Request):
            scheme = request.url.scheme
        else:
            _, (_scheme, *_), *_ = request
            scheme = _scheme.decode("ascii")
        return scheme


class Host(Pattern):
    lookups = (Lookup.EQUAL, Lookup.IN)
    key = "host"
    value: Union[str, Sequence[str]]

    def parse(self, request: RequestTypes) -> str:
        if isinstance(request, httpx.Request):
            host = request.url.host
        else:
            _, (_, _host, *_), *_ = request
            host = _host.decode("ascii")
        return host


class Port(Pattern):
    lookups = (Lookup.EQUAL, Lookup.IN)
    key = "port"
    value: Optional[int]

    def parse(self, request: RequestTypes) -> Optional[int]:
        scheme: Optional[str] = None
        if isinstance(request, httpx.Request):
            scheme = request.url.scheme
            port = request.url.port
        else:
            _, (_scheme, _, port, _), *_ = request
            if _scheme:
                scheme = _scheme.decode("ascii")
        scheme_port = get_scheme_port(scheme)
        return port or scheme_port


class Path(Pattern):
    lookups = (Lookup.EQUAL, Lookup.REGEX, Lookup.STARTS_WITH, Lookup.IN)
    key = "path"
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

    def parse(self, request: RequestTypes) -> str:
        if isinstance(request, httpx.Request):
            path = request.url.path
        else:
            _, (_, _, _, _path), *_ = request
            _path, _, _ = _path.partition(b"?")
            path = _path.decode("ascii")
        return path

    def strip_base(self, value: str) -> str:
        value = urljoin("/", value[len(self.base.value) :])
        return value


class Params(MultiItemsMixin, Pattern):
    lookups = (Lookup.CONTAINS, Lookup.EQUAL)
    key = "params"
    value: httpx.QueryParams

    def clean(self, value: QueryParamTypes) -> httpx.QueryParams:
        return httpx.QueryParams(value)

    def parse(self, request: RequestTypes) -> httpx.QueryParams:
        if isinstance(request, httpx.Request):
            query = request.url.query
        else:
            _, url, *_ = request
            query = httpx.URL(url).query

        return httpx.QueryParams(query)  # TODO: Cache params on request?


class URL(Pattern):
    lookups: Tuple[Lookup, ...] = (
        Lookup.CONTAINS,
        Lookup.EQUAL,
        Lookup.REGEX,
        Lookup.STARTS_WITH,
    )
    key = "url"
    value: Union[Pattern, str, RegexPattern[str]]

    def __hash__(self):
        if isinstance(self.value, Pattern):
            return hash(self.value)
        else:
            return super().__hash__()

    def __iter__(self):
        if isinstance(self.value, Pattern):
            yield from self.value
        else:
            yield self

    @classmethod
    def extract(cls, url: httpx.URL, **lookup: Lookup) -> List[Pattern]:
        patterns: List[Pattern] = []
        scheme_port = get_scheme_port(url.scheme)

        if url.scheme:
            patterns.append(Scheme(url.scheme, lookup=lookup.get("scheme")))
        if url.host:
            patterns.append(Host(url.host, lookup=lookup.get("host")))
        if url.port and url.port != scheme_port:
            patterns.append(Port(url.port, lookup=lookup.get("port")))
        if url._uri_reference.path:  # URL.path always returns "/"
            patterns.append(Path(url.path, lookup=lookup.get("path")))
        if url.query:
            patterns.append(Params(url.query, lookup=lookup.get("params")))

        if not patterns:
            raise ValueError(f"Invalid url: {url!r}")

        return patterns

    def clean(self, value: URLPatternTypes) -> Union[Pattern, str, RegexPattern[str]]:
        if self.lookup in (Lookup.EQUAL, Lookup.CONTAINS):
            pattern = None
            if isinstance(value, (str, tuple)):
                value = httpx.URL(value)

            assert isinstance(value, httpx.URL)

            patterns = self.extract(value, params=self.lookup)
            pattern = combine(patterns)

            return pattern

        elif self.lookup is Lookup.REGEX and isinstance(value, str):
            return re.compile(value)

        assert isinstance(value, (str, RegexPattern))

        return value

    def parse(self, request: RequestTypes) -> str:
        if isinstance(request, httpx.Request):
            url = str(request.url)
        else:
            _, _url, *_ = request
            url = str(httpx.URL(_url))
        return url

    def match(self, request: RequestTypes) -> Match:
        if isinstance(self.value, Pattern):
            return self.value.match(request)
        else:
            return super().match(request)


# TODO: Refactor this to register when subclassing
PATTERNS = {
    P.key: P
    for P in (
        Method,
        Headers,
        Cookies,
        Scheme,
        Host,
        Port,
        Path,
        Params,
        URL,
    )
}


def M(*patterns: Pattern, **lookups: Any) -> Pattern:
    for pattern__lookup, value in lookups.items():
        if not value:
            continue

        pattern_key, __, lookup_value = pattern__lookup.partition("__")
        if pattern_key not in PATTERNS:
            raise KeyError(f"{pattern_key!r} is not a valid Pattern")

        lookup = None if not lookup_value else Lookup(lookup_value)
        pattern = PATTERNS[pattern_key](value, lookup=lookup)
        patterns += (pattern,)

    return combine(patterns)


def get_scheme_port(scheme: Optional[str]) -> Optional[int]:
    return {"http": 80, "https": 443}.get(scheme)


def combine(
    patterns: Sequence[Pattern], op: Callable = operator.and_
) -> Optional[Pattern]:
    patterns = tuple(filter(None, patterns))
    if not patterns:
        return None
    return reduce(op, patterns)


def make_bases(url: Optional[str]) -> Dict[str, Pattern]:
    bases: Dict[str, Pattern] = {}
    if url:
        bases = {
            pattern.key: pattern
            for pattern in URL.extract(httpx.URL(url), path=Lookup.STARTS_WITH)
            if pattern.key != "params"
        }
    return bases


def merge_bases(pattern: Pattern, **bases: Pattern) -> Pattern:
    if not bases:
        return pattern

    if pattern:
        # Flatten pattern
        patterns = list(iter(pattern))

        if "host" in (_pattern.key for _pattern in patterns):
            # Pattern is "absolute", skip bases
            bases = None
        else:
            # Traverse pattern and set releated base
            for _pattern in patterns:
                base = bases.pop(_pattern.key, None)
                _pattern.base = base

    if bases:
        # Combine left over base patterns with pattern
        base_pattern = combine(list(bases.values()))
        if pattern:
            pattern = base_pattern & pattern
        else:
            pattern = base_pattern

    return pattern
