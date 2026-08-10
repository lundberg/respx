import email
import inspect
import sys
from collections import defaultdict

if sys.version_info >= (3, 14):  # pragma: no cover
    import annotationlib
else:  # pragma: no cover
    annotationlib = None
from datetime import datetime
from email.message import Message
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import parse_qsl

import httpx


class MultiItems(defaultdict):
    def __init__(self, values: Optional[Iterable[Tuple[str, Any]]] = None) -> None:
        super().__init__(tuple)
        if values is not None:
            for key, value in values:
                if isinstance(value, (tuple, list)):
                    self[key] += tuple(value)  # Convert list to tuple and extend
                else:
                    self[key] += (value,)  # Extend with value

    def get_list(self, key: str) -> List[Any]:
        return list(self[key])

    def multi_items(self) -> List[Tuple[str, str]]:
        return [(key, value) for key, values in self.items() for value in values]

    def append(self, key: str, value: Any) -> None:
        self[key] += (value,)


def _parse_multipart_form_data(
    content: bytes, *, content_type: str, encoding: str
) -> Tuple[MultiItems, MultiItems]:
    form_data = b"\r\n".join(
        (
            b"MIME-Version: 1.0",
            b"Content-Type: " + content_type.encode(encoding),
            b"\r\n" + content,
        )
    )
    data = MultiItems()
    files = MultiItems()
    for payload in email.message_from_bytes(form_data).get_payload():
        payload = cast(Message, payload)
        name = payload.get_param("name", header="Content-Disposition")
        assert isinstance(name, str)
        filename = payload.get_filename()
        content_type = payload.get_content_type()
        value = payload.get_payload(decode=True)
        assert isinstance(value, bytes)
        if content_type.startswith("text/") and filename is None:
            # Text field
            data.append(name, value.decode(payload.get_content_charset() or "utf-8"))
        else:
            # File field
            files.append(name, (filename, value))

    return data, files


def _parse_urlencoded_data(content: bytes, *, encoding: str) -> MultiItems:
    return MultiItems(
        (key, value)
        for key, value in parse_qsl(content.decode(encoding), keep_blank_values=True)
    )


def decode_data(request: httpx.Request) -> Tuple[MultiItems, MultiItems]:
    content = request.read()
    content_type = request.headers.get("Content-Type", "")

    if content_type.startswith("multipart/form-data"):
        data, files = _parse_multipart_form_data(
            content,
            content_type=content_type,
            encoding=request.headers.encoding,
        )
    else:
        data = _parse_urlencoded_data(
            content,
            encoding=request.headers.encoding,
        )
        files = MultiItems()

    return data, files


Self = TypeVar("Self", bound="SetCookie")


class SetCookie(
    NamedTuple(
        "SetCookie",
        [
            ("header_name", Literal["Set-Cookie"]),
            ("header_value", str),
        ],
    )
):
    def __new__(
        cls: Type[Self],
        name: str,
        value: str,
        *,
        path: Optional[str] = None,
        domain: Optional[str] = None,
        expires: Optional[Union[str, datetime]] = None,
        max_age: Optional[int] = None,
        http_only: bool = False,
        same_site: Optional[Literal["Strict", "Lax", "None"]] = None,
        secure: bool = False,
        partitioned: bool = False,
    ) -> Self:
        """
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#syntax
        """
        attrs: Dict[str, Union[str, bool]] = {name: value}
        if path is not None:
            attrs["Path"] = path
        if domain is not None:
            attrs["Domain"] = domain
        if expires is not None:
            if isinstance(expires, datetime):  # pragma: no branch
                expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
            attrs["Expires"] = expires
        if max_age is not None:
            attrs["Max-Age"] = str(max_age)
        if http_only:
            attrs["HttpOnly"] = True
        if same_site is not None:
            attrs["SameSite"] = same_site
            if same_site == "None":  # pragma: no branch
                secure = True
        if secure:
            attrs["Secure"] = True
        if partitioned:
            attrs["Partitioned"] = True

        string = "; ".join(
            _name if _value is True else f"{_name}={_value}"
            for _name, _value in attrs.items()
        )
        self = super().__new__(cls, "Set-Cookie", string)
        return self


def _fullargspec_from_signature(sig: "inspect.Signature") -> "inspect.FullArgSpec":
    """Build a :class:`inspect.FullArgSpec` from a :class:`inspect.Signature`."""
    args: List[str] = []
    varargs: Optional[str] = None
    varkw: Optional[str] = None
    kwonlyargs: List[str] = []
    kwonlydefaults: dict = {}
    pos_defaults: List[Any] = []
    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            args.append(name)
            if param.default is not param.empty:
                pos_defaults.append(param.default)
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            varargs = name
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            varkw = name
        else:  # inspect.Parameter.KEYWORD_ONLY
            kwonlyargs.append(name)
            if param.default is not param.empty:
                kwonlydefaults[name] = param.default

    return inspect.FullArgSpec(
        args,
        varargs,
        varkw,
        tuple(pos_defaults) if pos_defaults else None,
        kwonlyargs,
        kwonlydefaults or None,
        {},
    )


def getfuncargspec(func: Any) -> "inspect.FullArgSpec":
    """Return an ``inspect.FullArgSpec`` for *func* without evaluating annotations.

    :func:`inspect.getfullargspec` forces evaluation of a callable's annotations,
    which under PEP 649 (Python 3.14+) raises ``TypeError: unsupported callable``
    for callables that reference names only available under ``TYPE_CHECKING``
    (e.g. typing a SQLAlchemy ``AsyncSession`` fixture without importing it at
    runtime). respx only needs the parameter names (and positional defaults), so
    when that fails we read them via :func:`inspect.signature` with
    ``annotation_format`` set to ``ForwardRef`` on Python 3.14+ so unresolved names
    degrade to ``ForwardRef`` placeholders instead of raising.
    """
    try:
        return inspect.getfullargspec(func)
    except (TypeError, NameError, ValueError, AttributeError):
        pass

    try:
        if sys.version_info >= (3, 14) and annotationlib is not None:  # pragma: no cover
            sig = inspect.signature(
                func, annotation_format=annotationlib.Format.FORWARDREF
            )
        elif sys.version_info >= (3, 10):  # pragma: no cover
            sig = inspect.signature(func, eval_str=False)
        else:  # pragma: no cover
            sig = inspect.signature(func)
    except (TypeError, ValueError):  # pragma: no cover
        return inspect.FullArgSpec((), None, None, None, (), None, {})

    return _fullargspec_from_signature(sig)
