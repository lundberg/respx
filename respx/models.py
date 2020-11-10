import inspect
from collections.abc import Iterator
from typing import Any, Callable, Dict, NamedTuple, Optional, Tuple, Type, Union, cast
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
    SideEffectTypes,
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


def clone_response(response: httpx.Response, request: httpx.Request) -> httpx.Response:
    """
    Clones a httpx Response for given request.
    """
    response = httpx.Response(
        response.status_code,
        headers=response.headers,
        stream=response.stream,
        request=request,
        ext=dict(response.ext),
    )
    response.read()
    return response


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
        merged_context = dict(self.context)
        merged_context.update(context)
        return MockResponse(
            self.status_code,
            content=self.content,
            text=self.text,
            html=self.html,
            json=self.json,
            headers=self.headers,
            http_version=self.http_version,
            context=merged_context,
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

    def as_response(self) -> httpx.Response:
        content = self._content
        context = dict(self.context)
        request = decode_request(context.pop("request"))

        if callable(content):
            if inspect.iscoroutinefunction(self._content):
                raise NotImplementedError("Async content callback no longer supported.")
            content = content(request, **context)

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
            request=request,
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
        self._return_value: Union[MockResponse, httpx.Response] = None
        self._side_effect: Optional[SideEffectTypes] = None
        self._pass_through: Optional[bool] = None
        self.snapshot()

    def __hash__(self):
        if self.pattern:
            return hash(self.pattern)
        return id(self)

    def __repr__(self):
        return f"<Route {self.pattern!r}>"  # pragma: no cover

    def __call__(self, side_effect: Callable) -> Callable:
        self.side_effect = side_effect
        return side_effect

    def __mod__(self, response: Union[int, Dict[str, Any]]) -> "Route":
        if isinstance(response, int):
            self.return_value = httpx.Response(status_code=response)

        elif isinstance(response, dict):
            response.setdefault("status_code", 200)
            self.return_value = httpx.Response(**response)

        else:
            assert isinstance(
                response, (httpx.Response, MockResponse)
            ), f"Route can only % with int or dict, got {response!r}"
            self.return_value = response

        return self

    @property
    def return_value(self) -> Optional[Union[MockResponse, httpx.Response]]:
        return self._return_value

    @return_value.setter
    def return_value(
        self, return_value: Optional[Union[MockResponse, httpx.Response]]
    ) -> None:
        self.pass_through(None)
        self._return_value = return_value

    @property
    def side_effect(self) -> Optional[SideEffectTypes]:
        return self._side_effect

    @side_effect.setter
    def side_effect(self, side_effect: Optional[SideEffectTypes]) -> None:
        self.pass_through(None)
        if not side_effect:
            self._side_effect = None
        elif isinstance(side_effect, (tuple, list, Iterator)):
            self._side_effect = iter(side_effect)
        else:
            self._side_effect = side_effect

    def snapshot(self) -> None:
        self.__return_value = self._return_value
        self.__side_effect = self._side_effect
        self.__pass_through = self._pass_through
        self._calls = CallList(self.calls)

    def rollback(self, reset: bool = True) -> None:
        self._return_value = self.__return_value
        self._side_effect = self.__side_effect
        self._pass_through = self.__pass_through
        if reset:
            self.reset()

    def reset(self) -> None:
        self.calls[:] = self._calls

    def mock(
        self,
        return_value: Optional[Union[MockResponse, httpx.Response]] = None,
        *,
        side_effect: Optional[SideEffectTypes] = None,
    ) -> "Route":
        self.return_value = return_value
        self.side_effect = side_effect
        return self

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
        return self.mock(return_value=response)

    def pass_through(self, value: bool = True) -> "Route":
        self._pass_through = value
        return self

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

    def _next_side_effect(
        self,
    ) -> Union[Callable, Exception, Type[Exception], httpx.Response]:
        effect: Union[Callable, Exception, Type[Exception], httpx.Response]
        if isinstance(self._side_effect, Iterator):
            effect = next(self._side_effect)
        else:
            effect = cast(
                Union[Callable, Exception, Type[Exception]], self._side_effect
            )

        return effect

    def _call_side_effect(
        self, effect: Callable, request: httpx.Request, **kwargs: Any
    ) -> Optional[Union[httpx.Request, httpx.Response, MockResponse]]:
        argspec = inspect.getfullargspec(effect)
        if "response" in argspec.args or len(argspec.args) > 1 + len(kwargs):
            warn(
                "Side effect (callback) `response` arg is deprecated. "
                "Please instantiate httpx.Response inside your function.",
                category=DeprecationWarning,
            )
            args = (
                request,
                MockResponse(context={"request": request, **kwargs}),
            )
        else:
            args = (request,)  # type: ignore

        # Call side effect
        try:
            result = effect(*args, **kwargs)
        except Exception as error:
            raise SideEffectError(self, origin=error) from error

        # Validate result
        if result and not isinstance(
            result, (httpx.Response, MockResponse, httpx.Request)
        ):
            raise ValueError(
                f"Side effects must return; either `httpx.Response` or "
                f"`MockResponse`, `httpx.Request` for pass-through, "
                f"or `None` for a non-match. Got {result!r}"
            )

        return result

    def _resolve_side_effect(
        self, request: httpx.Request, **kwargs: Any
    ) -> Optional[Union[httpx.Request, httpx.Response, MockResponse]]:
        effect = self._next_side_effect()

        # Handle Exception `instance` side effect
        if isinstance(effect, Exception):
            raise SideEffectError(self, origin=effect)

        # Handle Exception `type` side effect
        Error: Type[Exception] = cast(Type[Exception], effect)
        if isinstance(effect, type) and issubclass(Error, Exception):
            raise SideEffectError(
                self,
                origin=(
                    Error("Mock Error", request=request)
                    if issubclass(Error, httpx.HTTPError)
                    else Error()
                ),
            )

        # Handle `Callable` side effect
        if callable(effect):
            result = self._call_side_effect(effect, request, **kwargs)
            return result

        return effect

    def resolve(
        self, request: httpx.Request, **kwargs: Any
    ) -> Optional[Union[httpx.Request, httpx.Response]]:
        result: Optional[Union[MockResponse, httpx.Response, httpx.Request]] = None

        if self._side_effect:
            result = self._resolve_side_effect(request, **kwargs)
            if result is None:
                return None  # Side effect resolved as a non-matching route

        elif self._return_value:
            result = self._return_value

        if isinstance(result, MockResponse):
            # Resolve MockResponse into httpx.Response
            try:
                result = result.clone(request=request, **kwargs)
                result = result.as_response()
            except Exception as error:
                raise SideEffectError(self, origin=error) from error

        if result is None:
            # Auto mock a new response
            result = httpx.Response(200, request=request)

        elif isinstance(result, httpx.Response) and not result._request:
            # Clone existing Response for immutability
            result = clone_response(result, request)

        return result

    def match(
        self, request: httpx.Request
    ) -> Optional[Union[httpx.Request, httpx.Response]]:
        """
        Matches and resolves request with given patterns and optional side effect.

        Returns None for a non-matching route, mocked response for a match,
        or input request for pass-through.
        """
        context = {}

        if self.pattern:
            match = self.pattern.match(request)
            if not match:
                return None
            context = match.context

        if self._pass_through:
            return request

        result = self.resolve(request, **context)
        return result


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
            self.side_effect = method

        if response:
            self.return_value = response


class SideEffectError(Exception):
    def __init__(self, route: Route, origin: Exception) -> None:
        self.route = route
        self.origin = origin
