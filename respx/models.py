import inspect
import re
from typing import (
    Any,
    AsyncIterable,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from unittest import mock
from urllib.parse import urljoin
from warnings import warn

import httpx
from httpcore import AsyncByteStream, SyncByteStream

URL = Tuple[bytes, bytes, Optional[int], bytes]
Headers = List[Tuple[bytes, bytes]]
Request = Tuple[
    bytes,  # http method
    URL,
    Headers,
    Union[Iterable[bytes], AsyncIterable[bytes]],  # body
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
    Union[Iterable[bytes], AsyncIterable[bytes]],  # body
    dict,  # ext
]

HeaderTypes = Union[
    httpx.Headers,
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]

DefaultType = TypeVar("DefaultType", bound=Any)

Kwargs = Dict[str, Any]
URLPatternTypes = Union[str, Pattern[str], URL, httpx.URL]
JSONTypes = Union[str, List, Dict]
ContentDataTypes = Union[bytes, str, JSONTypes, Callable, Exception]
QueryParamTypes = Union[bytes, str, List[Tuple[str, Any]], Dict[str, Any]]


def build_url(
    url: Optional[URLPatternTypes] = None,
    base: Optional[str] = None,
    params: Optional[QueryParamTypes] = None,
) -> Optional[Union[httpx.URL, Pattern[str]]]:
    url = url or ""
    if not base:
        base_url = httpx.URL("")
    elif base.endswith("/"):
        base_url = httpx.URL(base)
    else:
        base_url = httpx.URL(base + "/")

    if not url and not base:
        return None
    elif isinstance(url, (str, tuple, httpx.URL)):
        return base_url.join(httpx.URL(url, params=params))
    elif isinstance(url, Pattern):
        if params is not None:
            if r"\?" in url.pattern and params is not None:
                raise ValueError(
                    "Request url pattern contains a query string, which is not "
                    "supported in conjuction with params argument."
                )
            query_params = str(httpx.QueryParams(params))
            url = re.compile(url.pattern + re.escape(fr"?{query_params}"))

        return re.compile(urljoin(str(base_url), url.pattern))
    else:
        raise ValueError(
            "Request url pattern must be str or compiled regex, got {}.".format(
                type(url).__name__
            )
        )


def decode_request(request: Request) -> httpx.Request:
    """
    Build a httpx Request from httpcore request args.
    """
    method, url, headers, stream = request
    return httpx.Request(method, url, headers=headers, stream=stream)


def decode_response(
    response: Optional[Response], request: httpx.Request
) -> Optional[httpx.Response]:
    """
    Build a httpx Response from httpcore response args.
    """
    if response is None:
        return None

    status_code, headers, stream, ext = response
    return httpx.Response(
        status_code, headers=headers, stream=stream, ext=ext, request=request
    )


class Call(NamedTuple):
    request: httpx.Request
    response: Optional[httpx.Response]


class RawCall:
    def __init__(self, raw_request: Request, raw_response: Optional[Response] = None):
        self.raw_request = raw_request
        self.raw_response = raw_response

        self._call: Optional[Call] = None

    @property
    def call(self) -> Call:
        if self._call is None:
            self._call = self._decode_call()

        return self._call

    def _decode_call(self) -> Call:
        # Decode raw request/response as HTTPX models
        request = decode_request(self.raw_request)
        response = decode_response(self.raw_response, request=request)

        # Pre-read request/response, but only if mocked, not for pass-through streams
        if response and not isinstance(
            response.stream, (SyncByteStream, AsyncByteStream)
        ):
            request.read()
            response.read()

        return Call(request=request, response=response)


class CallList(list, mock.NonCallableMock):
    def __iter__(self) -> Generator[Call, None, None]:
        for raw_call in super().__iter__():
            yield raw_call.call

    def __getitem__(self, item: int) -> Call:  # type: ignore
        raw_call: RawCall = super().__getitem__(item)
        return raw_call.call

    @property
    def called(self) -> bool:  # type: ignore
        return bool(self)

    @property
    def call_count(self) -> int:  # type: ignore
        return len(self)

    @property
    def last(self) -> Optional[Call]:
        return self[-1] if self else None

    def record(self, raw_request: Request, raw_response: Response) -> RawCall:
        raw_call = RawCall(raw_request=raw_request, raw_response=raw_response)
        self.append(raw_call)
        return raw_call


class ResponseTemplate:
    _content: Optional[ContentDataTypes]
    _text: Optional[str]
    _html: Optional[str]
    _json: Optional[JSONTypes]

    def __init__(
        self,
        status_code: Optional[int] = None,
        *,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        http_version: Optional[str] = None,
        context: Optional[Kwargs] = None,
    ) -> None:
        self.http_version = http_version
        self.status_code = status_code or 200
        self.context = context if context is not None else {}

        self.headers = httpx.Headers(headers) if headers else httpx.Headers()
        if content_type:
            self.headers["Content-Type"] = content_type

        # Set body variants in reverse priority order
        self.json = json
        self.html = html
        self.text = text
        self.content = content

    def clone(self, context: Optional[Kwargs] = None) -> "ResponseTemplate":
        return ResponseTemplate(
            self.status_code,
            content=self.content,
            text=self.text,
            html=self.html,
            json=self.json,
            headers=self.headers,
            http_version=self.http_version,
            context=context,
        )

    def prepare(
        self,
        content: Optional[ContentDataTypes],
        *,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
    ) -> Tuple[
        Optional[ContentDataTypes], Optional[str], Optional[str], Optional[JSONTypes]
    ]:
        if content is not None:
            text = None
            html = None
            json = None
            if isinstance(content, str):
                text = content
                content = None
            elif isinstance(content, (list, dict)):
                json = content
                content = None
        elif text is not None:
            html = None
            json = None
        elif html is not None:
            json = None

        return content, text, html, json

    @property
    def content(self) -> Optional[ContentDataTypes]:
        return self._content

    @content.setter
    def content(self, content: Optional[ContentDataTypes]) -> None:
        self._content, self.text, self.html, self.json = self.prepare(
            content, text=self.text, html=self.html, json=self.json
        )

    @property
    def text(self) -> Optional[str]:
        return self._text

    @text.setter
    def text(self, text: Optional[str]) -> None:
        self._text = text
        if text is not None:
            self._content = None
            self._html = None
            self._json = None

    @property
    def html(self) -> Optional[str]:
        return self._html

    @html.setter
    def html(self, html: Optional[str]) -> None:
        self._html = html
        if html is not None:
            self._content = None
            self._text = None
            self._json = None

    @property
    def json(self) -> Optional[JSONTypes]:
        return self._json

    @json.setter
    def json(self, json: Optional[JSONTypes]) -> None:
        self._json = json
        if json is not None:
            self._content = None
            self._text = None
            self._html = None

    def encode_response(self, content: ContentDataTypes) -> Response:
        if isinstance(content, Exception):
            raise content

        content, text, html, json = self.prepare(
            content, text=self.text, html=self.html, json=self.json
        )

        # Comply with httpx Response content type hints
        assert content is None or isinstance(content, bytes)

        response = httpx.Response(
            self.status_code,
            headers=self.headers,
            content=content,
            text=text,
            html=html,
            json=json,
        )

        if self.http_version:
            response.ext["http_version"] = self.http_version

        return (
            response.status_code,
            response.headers.raw,
            response.stream,
            response.ext,
        )

    @property
    def raw(self):
        content = self._content
        if callable(content):
            kwargs = dict(self.context)
            request = decode_request(kwargs.pop("request"))
            content = content(request, **kwargs)

        return self.encode_response(content)

    @property
    async def araw(self):
        if callable(self._content) and inspect.iscoroutinefunction(self._content):
            kwargs = dict(self.context)
            request = decode_request(kwargs.pop("request"))
            content = await self._content(request, **kwargs)
            return self.encode_response(content)

        return self.raw


class RequestPattern:
    def __init__(
        self,
        method: Union[str, Callable],
        url: Optional[URLPatternTypes],
        params: Optional[QueryParamTypes] = None,
        response: Optional[ResponseTemplate] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._match_func: Optional[Callable] = None

        if callable(method):
            self.method = None
            self.url = None
            self.pass_through = None
            self._match_func = method
        else:
            self.method = method.upper()
            self.url = build_url(url, base=base_url, params=params)
            self.pass_through = pass_through

        self.response = response or ResponseTemplate()
        self.alias = alias
        self.calls = CallList()

    @property
    def called(self) -> bool:
        return self.calls.called

    @property
    def call_count(self) -> int:
        return self.calls.call_count

    @property
    def stats(self):
        warn(
            ".stats property is deprecated. Please, use .calls",
            category=DeprecationWarning,
        )
        return self.calls

    def match(self, request: Request) -> Optional[Union[Request, ResponseTemplate]]:
        """
        Matches request with configured pattern;
        custom matcher function or http method + url pattern.

        Returns None for a non-matching pattern, mocked response for a match,
        or input request for pass-through.
        """
        matches = False
        url_params: Kwargs = {}

        if self.pass_through:
            return request

        if self._match_func:
            _request = decode_request(request)
            response = self.response.clone(context={"request": request})
            result = self._match_func(_request, response)
            if result == _request:  # Detect pass through
                result = request
            return result

        request_method, _request_url, *_ = request
        if self.method != request_method.decode():
            return None

        if not self.url:
            matches = True
        elif isinstance(self.url, httpx.URL):
            matches = self.url.raw == _request_url
        else:
            match = self.url.match(str(httpx.URL(_request_url)))
            if match:
                matches = True
                url_params = match.groupdict()

        if matches:
            return self.response.clone(context={"request": request, **url_params})

        return None
