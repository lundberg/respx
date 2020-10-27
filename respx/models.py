import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)
from unittest import mock
from warnings import warn

import httpx

from .patterns import M, Pattern
from .types import (
    ContentDataTypes,
    HeaderTypes,
    JSONTypes,
    Kwargs,
    QueryParamTypes,
    RequestTypes,
    Response,
    URLPatternTypes,
)


def decode_request(request: RequestTypes) -> httpx.Request:
    """
    Build a httpx Request from httpcore request args.
    """
    if isinstance(request, httpx.Request):
        return request
    method, url, headers, stream = request
    return httpx.Request(method, url, headers=headers, stream=stream)


def encode_response(response: httpx.Response) -> Response:
    """
    Builds a raw response tuple from httpx Response.
    """
    return (
        response.status_code,
        response.headers.raw,
        response.stream,
        response.ext,
    )


class Call(NamedTuple):
    request: httpx.Request
    response: Optional[httpx.Response]


class CallList(list, mock.NonCallableMock):
    @property
    def called(self) -> bool:  # type: ignore
        return bool(self)

    @property
    def call_count(self) -> int:  # type: ignore
        return len(self)

    @property
    def last(self) -> Optional[Call]:
        return self[-1] if self else None

    def record(
        self, request: httpx.Request, response: Optional[httpx.Response]
    ) -> Call:
        call = Call(request=request, response=response)
        self.append(call)
        return call


class MockResponse:
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

    def clone(self, context: Optional[Kwargs] = None) -> "MockResponse":
        return MockResponse(
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

        return encode_response(response)

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


class ResponseTemplate(MockResponse):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warn(
            "ResponseTemplate is deprecated. Please use MockResponse.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)


class Route:
    def __init__(
        self,
        *patterns: Pattern,
        **lookups: Any,
    ) -> None:
        self.pattern = M(*patterns, **lookups)
        self.name: Optional[str] = None
        self.calls = CallList()
        self._responses: List[Union[MockResponse, httpx.Response]] = []
        self._pass_through: Optional[bool] = None
        self._callback: Optional[Callable] = None

    def __hash__(self):
        if self.pattern:
            return hash(self.pattern)
        elif self._pass_through is not None:
            return hash(self._pass_through)
        elif self._callback:
            return hash(self._callback)
        return id(self)

    def __mod__(
        self, response: Union[int, Dict[str, Any], MockResponse, httpx.Response]
    ) -> "Route":
        if isinstance(response, int):
            response = httpx.Response(response)
        if isinstance(response, dict):
            response.setdefault("status_code", 200)
            response = httpx.Response(**response)
        return self.add_response(response)

    def respond(
        self,
        status_code: Optional[int] = None,
        *,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        http_version: Optional[str] = None,
    ) -> "Route":
        response = MockResponse(
            status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            http_version=http_version,
        )
        return self.add_response(response)

    def add_response(self, response: Union[MockResponse, httpx.Response]) -> "Route":
        self._responses.append(response)
        return self

    def get_response(self, **context: Any) -> Union[MockResponse, httpx.Response]:
        response: Union[MockResponse, httpx.Response]

        if len(self._responses) == 0:
            response = MockResponse()
            self.add_response(response)
        elif len(self._responses) == 1:
            response = self._responses[0]
        else:
            response = self._responses.pop(0)  # Pop stacked responses in order

        if isinstance(response, MockResponse):
            return response.clone(context=context)

        return response

    def callback(self, callback: Callable) -> "Route":
        self._callback = callback
        self._pass_through = None
        return self

    def pass_through(self, value: bool = True) -> "Route":
        self._pass_through = value
        if value:
            self._callback = None
            self._responses.clear()
        return self

    @property
    def is_callback(self) -> bool:
        return bool(self._callback)

    @property
    def is_pass_through(self) -> bool:
        return bool(self._pass_through)

    @property
    def alias(self) -> Optional[str]:
        warn(
            ".alias property is deprecated. Please, use .name",
            category=DeprecationWarning,
        )
        return self.name

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

    def match(
        self, request: RequestTypes
    ) -> Optional[Union[RequestTypes, MockResponse, httpx.Response]]:
        """
        Matches request with given patterns.

        Returns None for a non-matching pattern, mocked response for a match,
        or input request for pass-through.
        """
        response: Union[RequestTypes, MockResponse, httpx.Response]
        context = {}

        if not any((self.pattern, self._pass_through, self._callback)):
            return None

        if self.pattern:
            match = self.pattern.match(request)
            if not match:
                return None
            context = match.context

        if self._pass_through:
            return request

        if self._callback:
            _request = decode_request(request)
            response = self.get_response(request=request)

            result = self._callback(_request, response)

            if result == _request:  # Detect pass through
                result = request

            return result

        return self.get_response(request=request, **context)


class RequestPattern(Route):
    def __init__(
        self,
        method: Union[str, Callable] = None,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        response: Optional[MockResponse] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        warn(
            "RequestPattern is deprecated. Please use Route.",
            category=DeprecationWarning,
        )

        super().__init__(
            method=method if not callable(method) else None,
            base_url=base_url,
            url=url,
            params=params,
        )

        self.name = alias
        self._pass_through = pass_through

        if callable(method):
            self.callback(method)

        if response:
            self.add_response(response)
