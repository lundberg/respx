from typing import (
    Any,
    AsyncIterable,
    Callable,
    Dict,
    Iterable,
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
from httpcore import AsyncByteStream, SyncByteStream

URL = Tuple[
    bytes,  # scheme
    bytes,  # host
    Optional[int],  # port
    bytes,  # path
]
Headers = List[Tuple[bytes, bytes]]
ByteStream = Union[Iterable[bytes], AsyncIterable[bytes]]
Request = Tuple[
    bytes,  # http method
    URL,
    Headers,
    ByteStream,  # body
]
SyncResponse = Tuple[
    int,  # status code
    Headers,
    SyncByteStream,  # body
    dict,  # ext
]
AsyncResponse = Tuple[
    int,  # status code
    Headers,
    AsyncByteStream,  # body
    dict,  # ext
]
Response = Tuple[
    int,  # status code
    Headers,
    ByteStream,  # body
    dict,  # ext
]

HeaderTypes = Union[
    httpx.Headers,
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]
CookieTypes = Union[Dict[str, str], Sequence[Tuple[str, str]]]

DefaultType = TypeVar("DefaultType", bound=Any)

Kwargs = Dict[str, Any]
URLPatternTypes = Union[str, Pattern[str], URL, httpx.URL]
JSONTypes = Union[str, List, Dict]
ContentDataTypes = Union[bytes, str, JSONTypes, Callable, Exception]
QueryParamTypes = Union[bytes, str, List[Tuple[str, Any]], Dict[str, Any]]
RequestTypes = Union[Request, httpx.Request]
SideEffectListTypes = Union[httpx.Response, Exception, Type[Exception]]
SideEffectTypes = Union[
    Callable,
    Exception,
    Type[Exception],
    Sequence[SideEffectListTypes],
    Iterator[SideEffectListTypes],
]
