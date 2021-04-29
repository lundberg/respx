from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import httpx

URL = Tuple[
    bytes,  # scheme
    bytes,  # host
    Optional[int],  # port
    bytes,  # path
]
Headers = List[Tuple[bytes, bytes]]
ByteStream = Union[httpx.SyncByteStream, httpx.AsyncByteStream]
Request = Tuple[
    bytes,  # http method
    URL,
    Headers,
    ByteStream,  # body
]
SyncResponse = Tuple[
    int,  # status code
    Headers,
    httpx.SyncByteStream,  # body
    dict,  # ext
]
AsyncResponse = Tuple[
    int,  # status code
    Headers,
    httpx.AsyncByteStream,  # body
    dict,  # ext
]
Response = Tuple[
    int,  # status code
    Headers,
    ByteStream,  # body
    dict,  # ext
]
RequestHandler = Callable[[httpx.Request], httpx.Response]
AsyncRequestHandler = Callable[[httpx.Request], Awaitable[httpx.Response]]

HeaderTypes = Union[
    httpx.Headers,
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]
CookieTypes = Union[Dict[str, str], Sequence[Tuple[str, str]]]

DefaultType = TypeVar("DefaultType", bound=Any)

URLPatternTypes = Union[str, Pattern[str], URL, httpx.URL]
QueryParamTypes = Union[bytes, str, List[Tuple[str, Any]], Dict[str, Any]]
RequestTypes = Union[Request, httpx.Request]

ResolvedResponseTypes = Optional[Union[httpx.Request, httpx.Response]]
RouteResultTypes = Union[ResolvedResponseTypes, Awaitable[ResolvedResponseTypes]]
CallableSideEffect = Callable[..., RouteResultTypes]
SideEffectListTypes = Union[httpx.Response, Exception, Type[Exception]]
SideEffectTypes = Union[
    CallableSideEffect,
    Exception,
    Type[Exception],
    Sequence[SideEffectListTypes],
    Iterator[SideEffectListTypes],
]
