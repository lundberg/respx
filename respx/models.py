import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from unittest import mock
from warnings import warn

import httpx

from .patterns import M, Pattern
from .types import (
    ByteStream,
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

    def clone(self, **context: Any) -> "MockResponse":
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

    def as_response(self, request: Optional[httpx.Request]) -> httpx.Response:
        content = self._content

        if callable(content):
            if inspect.iscoroutinefunction(self._content):
                raise NotImplementedError("Async content callback no longer supported.")
            kwargs = dict(self.context)
            request = decode_request(kwargs.pop("request"))
            content = content(request, **kwargs)

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
            request=decode_request(self.context.get("request")),
        )

        if self.http_version:
            response.ext["http_version"] = self.http_version

        return response


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
        self.name: Optional[str] = None  # TODO: Drop or add setter to prevent change
        self.calls = CallList()
        self._responses: List[Union[MockResponse, httpx.Response]] = []
        self._side_effect: Optional[Union[Callable, Exception, Type[Exception]]] = None
        self._pass_through: Optional[bool] = None

    def __hash__(self):
        if self.pattern:
            return hash(self.pattern)
        elif self._pass_through is not None:
            return hash(self._pass_through)
        elif self._side_effect:
            return hash(self._side_effect)
        return id(self)

    def __repr__(self):
        return f"<Route {self.pattern!r}>"  # pragma: no cover

    def __call__(self, side_effect: Callable) -> Callable:
        self.side_effect(side_effect)
        return side_effect

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
        status_code: int = 200,
        *,
        headers: Optional[HeaderTypes] = None,
        content: Optional[Union[str, bytes, ByteStream]] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        stream: Optional[ByteStream] = None,
        **kwargs: Any,
    ) -> "Route":
        response = httpx.Response(
            status_code,
            headers=headers,
            content=content,
            text=text,
            html=html,
            json=json,
            stream=stream,
            **kwargs,
        )
        return self.add_response(response)

    def add_response(self, response: Union[MockResponse, httpx.Response]) -> "Route":
        self._responses.append(response)
        return self

    def side_effect(
        self, side_effect: Union[Callable, Exception, List[httpx.Response]]
    ) -> "Route":
        self.pass_through(None)
        if isinstance(side_effect, list):
            self._responses[:] = side_effect
            self._side_effect = None
        elif isinstance(side_effect, Exception):
            self._side_effect = side_effect
        else:
            self._side_effect = side_effect
        return self

    def pass_through(self, value: bool = True) -> "Route":
        self._pass_through = value
        if value is not None:
            self._side_effect = None
            self._responses.clear()
        return self

    @property
    def has_side_effect(self) -> bool:
        return bool(self._side_effect)

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

    def resolve(
        self, request: httpx.Request, **kwargs: Any
    ) -> Optional[Union[httpx.Request, httpx.Response]]:
        response: Optional[Union[MockResponse, httpx.Response, httpx.Request]] = None

        if self._side_effect:
            Error: Type[Exception] = cast(Type[Exception], self._side_effect)

            if isinstance(self._side_effect, Exception):
                # Eception instance
                raise self._side_effect

            elif isinstance(self._side_effect, type) and issubclass(Error, Exception):
                # Exception type
                if issubclass(Error, httpx.HTTPError):
                    raise Error("Mock Error", request=request)
                else:
                    raise Error()

            else:
                # Callable
                argspec = inspect.getfullargspec(self._side_effect)
                if "response" in argspec.args or len(argspec.args) > 1 + len(kwargs):
                    warn(
                        "Side effect (callback) `response` arg is deprecated. "
                        "Please instantiate httpx.Response inside your function.",
                        category=DeprecationWarning,
                    )
                    args = (
                        request,
                        MockResponse(context=kwargs),
                    )
                else:
                    args = (request,)  # type: ignore

                try:
                    # Call side effect
                    response = self._side_effect(*args, **kwargs)
                except Exception as error:
                    raise SideEffectError(self, origin=error) from error

                if response and not isinstance(
                    response, (httpx.Response, MockResponse, httpx.Request)
                ):
                    raise ValueError(
                        f"Side effects must return; either `httpx.Response` or "
                        f"`MockResponse`, `httpx.Request` for pass-through, "
                        f"or `None` for a non-match. Got {response!r}"
                    )

                if response is None:
                    # Side effect resolved as a non-matching route
                    return None

        elif len(self._responses) == 1:
            # Single repeated response
            response = self._responses[0]

        elif len(self._responses) > 1:
            # Stacked response, pop in added order
            response = self._responses.pop(0)

        if isinstance(response, MockResponse):
            # Resolve MockResponse as httpx.Response
            try:
                mock_response = response.clone(request=request, **kwargs)
                response = mock_response.as_response(request)
            except Exception as error:
                raise SideEffectError(self, origin=error) from error

        if response is None:
            # Create new response
            response = httpx.Response(200, request=request)

        elif isinstance(response, httpx.Response) and not response._request:
            # Clone existing response for immutability
            response = httpx.Response(
                response.status_code,
                headers=response.headers,
                stream=response.stream,
                request=request,
                ext=dict(response.ext),
            )
            response.read()

        return response

    def match(
        self, request: httpx.Request
    ) -> Optional[Union[httpx.Request, httpx.Response]]:
        """
        Matches and resolves request with given patterns and optional side effect.

        Returns None for a non-matching route, mocked response for a match,
        or input request for pass-through.
        """
        context = {}

        if not self.pattern and not self._side_effect and self._pass_through is None:
            return None

        if self.pattern:
            match = self.pattern.match(request)
            if not match:
                return None
            context = match.context

        if self._pass_through:
            return request

        response = self.resolve(request, **context)

        return response


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
            self.side_effect(method)

        elif response:
            self.add_response(response)


class SideEffectError(Exception):
    def __init__(self, route: Route, origin: Exception) -> None:
        self.route = route
        self.origin = origin
