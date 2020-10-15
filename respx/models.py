import inspect
import re
from typing import (
    TYPE_CHECKING,
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

import httpx
from httpcore import AsyncByteStream, SyncByteStream

if TYPE_CHECKING:
    from unittest.mock import _CallList  # pragma: nocover


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


class CallList(list):
    def __iter__(self) -> Generator[Call, None, None]:
        yield from super().__iter__()

    @classmethod
    def from_unittest_call_list(cls, call_list: "_CallList") -> "CallList":
        return cls(Call(request, response) for (request, response), _ in call_list)

    @property
    def last(self) -> Optional[Call]:
        return self[-1] if self else None


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
            self.set_url(url, base=base_url, params=params)
            self.pass_through = pass_through

        self.response = response or ResponseTemplate()
        self.alias = alias
        self.stats = mock.MagicMock()

    @property
    def called(self) -> bool:
        return self.stats.called

    @property
    def call_count(self) -> int:
        return self.stats.call_count

    @property
    def calls(self) -> CallList:
        return CallList.from_unittest_call_list(self.stats.call_args_list)

    def get_url(self) -> Optional["URLPattern"]:
        return self._url

    def set_url(
        self,
        url: Optional[URLPatternTypes],
        base: Optional[str] = None,
        params: Optional[QueryParamTypes] = None,
    ) -> None:
        self._url = URLPattern(url, base=base, params=params)

    url = property(get_url, set_url)

    def match(self, request: Request) -> Optional[Union[Request, ResponseTemplate]]:
        """
        Matches request with configured pattern;
        custom matcher function or http method + url pattern.

        Returns None for a non-matching pattern, mocked response for a match,
        or input request for pass-through.
        """

        if self.pass_through:
            return request

        if self._match_func:
            _request = decode_request(request)
            response = self.response.clone(context={"request": request})
            result = self._match_func(_request, response)
            if result == _request:  # Detect pass through
                result = request
            return result

        request_method, request_url, *_ = request
        if self.method != request_method.decode():
            return None

        matches, url_params = self.url.matches(request_url)

        if matches:
            return self.response.clone(context={"request": request, **url_params})

        return None


class URLPattern:
    def __init__(
        self,
        url: URLPatternTypes,
        base: Optional[str] = None,
        params: Optional[QueryParamTypes] = None,
    ):
        self._regex: Optional[Pattern[str]] = None
        self._url: Optional[httpx.URL] = None
        self._params: Optional[httpx.QueryParams] = None

        url = url or None

        if not base:
            base_url = httpx.URL("")
        else:
            base_url = httpx.URL(base if base.endswith("/") else base + "/")

            if not url:
                url = base_url

        if params is not None:
            self._params = httpx.QueryParams(params)

        if isinstance(url, (str, tuple, httpx.URL)):
            self._url = base_url.join(httpx.URL(url))

            if self._url.query:
                self._url, extracted_params = self._extract_params(self._url)
                if self._params:
                    # kwarg-based params should be more important than URL-based params
                    extracted_params.update(self._params)

                self._params = extracted_params

            if self._url.path == "/":
                # add "/" if missing (URL.path returns it with default '/')
                self._url = self._url.copy_with(raw_path=b"/")

        elif isinstance(url, Pattern):
            if r"\?" in url.pattern:
                raise ValueError(
                    'Request url pattern contains a query string. Please, use "params" argument',
                )
            self._regex = (
                url if base is None else re.compile(urljoin(base, url.pattern))
            )
        elif url is not None:
            raise ValueError(
                "Request url pattern must be str or compiled regex, got {}.".format(
                    type(url).__name__
                )
            )

    def matches(self, url_parts: URL) -> Tuple[bool, Dict[str, Any]]:
        url = httpx.URL(url_parts)
        url, params = self._extract_params(url)

        if self._params and self._params != params:
            return False, {}

        if self._regex is not None:
            match = self._regex.match(str(url))
            if match:
                return True, match.groupdict()
            return False, {}

        elif self._url is not None:
            return self._url == url, {}

        return True, {}

    @staticmethod
    def _extract_params(url: httpx.URL) -> Tuple[httpx.URL, httpx.QueryParams]:
        params = httpx.QueryParams(url.query)
        url = url.copy_with(raw_path=url.path.encode())
        return url, params
