import inspect
import ssl
import typing
from contextlib import contextmanager
from functools import partial, partialmethod, wraps

import asynctest
from httpx import Client, TimeoutConfig
from httpx.backends.base import BaseSocketStream
from httpx.dispatch.base import Dispatcher
from httpx.models import Headers, HeaderTypes, Request, Response

from .models import ContentDataTypes, RequestPattern, ResponseTemplate, URLResponse

__all__ = ["HTTPXMock"]

_send = Client.send  # Pass-through reference


class HTTPXMock:
    def __init__(
        self,
        assert_all_called: bool = True,
        assert_all_mocked: bool = True,
        base_url: typing.Optional[str] = None,
        local: bool = True,
    ) -> None:
        self._is_local = local
        self._assert_all_called = assert_all_called
        self._assert_all_mocked = assert_all_mocked
        self._base_url = base_url
        self._patchers: typing.List[asynctest.mock._patch] = []
        self._patterns: typing.List[RequestPattern] = []
        self.aliases: typing.Dict[str, RequestPattern] = {}
        self.stats = asynctest.mock.MagicMock()
        self.calls: typing.List[typing.Tuple[Request, typing.Optional[Response]]] = []

    def __call__(
        self,
        func: typing.Optional[typing.Callable] = None,
        assert_all_called: typing.Optional[bool] = None,
        assert_all_mocked: typing.Optional[bool] = None,
        base_url: typing.Optional[str] = None,
    ) -> typing.Union["HTTPXMock", typing.Callable]:
        """
        Decorator or Context Manager.

        Use decorator/manager with parentheses for local state, or without parentheses
        for global state, i.e. shared patterns added outside of scope.
        """
        if func is None:
            # A. First stage of "local" decorator, WITH parentheses.
            # B. Only stage of "local" context manager, WITH parentheses,
            #    "global" context maanager hits __enter__ directly.
            settings: typing.Dict[str, typing.Any] = {"base_url": base_url}
            if assert_all_called is not None:
                settings["assert_all_called"] = assert_all_called
            if assert_all_mocked is not None:
                settings["assert_all_mocked"] = assert_all_mocked
            return self.__class__(**settings)

        # Async Decorator
        @wraps(func)
        async def async_decorator(*args, **kwargs):
            assert func is not None
            if self._is_local:
                kwargs["httpx_mock"] = self
            async with self:
                return await func(*args, **kwargs)

        # Sync Decorator
        @wraps(func)
        def sync_decorator(*args, **kwargs):
            assert func is not None
            if self._is_local:
                kwargs["httpx_mock"] = self
            with self:
                return func(*args, **kwargs)

        # Dispatch async/sync decorator, depening on decorated function
        # A. Second stage of "local" decorator, WITH parentheses.
        # A. Only stage of "global" decorator, WITHOUT parentheses.
        return async_decorator if inspect.iscoroutinefunction(func) else sync_decorator

    def __enter__(self) -> "HTTPXMock":
        self.start()
        return self

    async def __aenter__(self) -> "HTTPXMock":
        return self.__enter__()

    def __exit__(self, *args: typing.Any) -> None:
        try:
            if self._assert_all_called:
                self.assert_all_called()
        finally:
            self.stop()

    async def __aexit__(self, *args: typing.Any) -> None:
        self.__exit__(*args)

    def start(self) -> None:
        """
        Starts mocking httpx.
        """
        # Unbound -> bound spy version of Client.send
        async def unbound_send(
            client: Client, request: Request, **kwargs: typing.Any
        ) -> Response:
            return await self.__Client__send__spy(client, request, **kwargs)

        # Patch Client.send
        patcher = asynctest.mock.patch("httpx.Client.send", new=unbound_send)
        patcher.start()

        self._patchers.append(patcher)

    def stop(self, reset: bool = True) -> None:
        """
        Stops mocking httpx.
        """
        while self._patchers:
            patcher = self._patchers.pop()
            patcher.stop()

        if reset:
            self.reset()

    def reset(self):
        self._patchers.clear()
        self._patterns.clear()
        self.aliases.clear()
        self.calls.clear()
        self.stats.reset_mock()

    def assert_all_called(self):
        assert all(
            (pattern.called for pattern in self._patterns)
        ), "RESPX: some mocked requests were not called!"

    def add(self, pattern: RequestPattern, alias: typing.Optional[str] = None) -> None:
        self._patterns.append(pattern)
        if alias:
            self.aliases[alias] = pattern

    def request(
        self,
        method: typing.Union[str, typing.Callable],
        url: typing.Optional[typing.Union[str, typing.Pattern]] = None,
        status_code: typing.Optional[int] = None,
        content: typing.Optional[ContentDataTypes] = None,
        content_type: typing.Optional[str] = None,
        headers: typing.Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: typing.Optional[str] = None,
    ) -> RequestPattern:
        """
        Adds a request pattern with given mocked response details.
        """
        headers = Headers(headers or {})
        if content_type:
            headers["Content-Type"] = content_type

        response = ResponseTemplate(status_code, headers, content)
        pattern = RequestPattern(
            method,
            url,
            response,
            pass_through=pass_through,
            alias=alias,
            base_url=self._base_url,
        )

        self.add(pattern, alias=alias)

        return pattern

    get = partialmethod(request, "GET")
    post = partialmethod(request, "POST")
    put = partialmethod(request, "PUT")
    patch = partialmethod(request, "PATCH")
    delete = partialmethod(request, "DELETE")
    head = partialmethod(request, "HEAD")
    options = partialmethod(request, "OPTIONS")

    def __getitem__(self, alias: str) -> typing.Optional[RequestPattern]:
        return self.aliases.get(alias)

    def _match(
        self, request: Request
    ) -> typing.Tuple[
        typing.Optional[RequestPattern], typing.Optional[ResponseTemplate]
    ]:
        matched_pattern: typing.Optional[RequestPattern] = None
        matched_pattern_index: typing.Optional[int] = None
        response: typing.Optional[ResponseTemplate] = None

        for i, pattern in enumerate(self._patterns):
            match = pattern.match(request)
            if not match:
                continue

            if matched_pattern_index is not None:
                # Multiple matches found, drop and use the first one
                self._patterns.pop(matched_pattern_index)
                break

            matched_pattern = pattern
            matched_pattern_index = i

            if isinstance(match, ResponseTemplate):
                # Mock response
                response = match
            elif isinstance(match, Request):
                # Pass-through request
                response = None
            else:
                raise ValueError(
                    (
                        "Matched request pattern must return either a "
                        'ResponseTemplate or a Request, got "{}"'
                    ).format(type(match))
                )

        # Assert we always get a pattern match, if check is enabled
        assert (
            not self._assert_all_mocked
            or self._assert_all_mocked
            and matched_pattern is not None
        ), f"RESPX: {request!r} not mocked!"

        if matched_pattern is None:
            response = ResponseTemplate()

        return matched_pattern, response

    def _capture(
        self,
        request: Request,
        response: typing.Optional[Response],
        pattern: typing.Optional[RequestPattern] = None,
    ) -> None:
        """
        Captures request and response calls for statistics.
        """
        if pattern:
            pattern.stats(request, response)

        self.stats(request, response)

        # Copy stats due to unwanted use of property refs in the high-level api
        self.calls[:] = (
            (request, response) for (request, response), _ in self.stats.call_args_list
        )

    @contextmanager
    def _patch_backend(
        self, dispatch: Dispatcher, request: Request
    ) -> typing.Iterator[typing.Callable]:
        patchers = []

        # 1. Match request against added patterns
        pattern, response = self._match(request)

        if response is not None:
            # 2. Patch request url with response for later pickup in patched backend
            request.url = URLResponse(request.url, response)

            backend = getattr(dispatch, "backend", None)
            if backend is not None:
                # 3A. Start patching backend's open_tcp_stream() and open_uds_stream()
                mockers = (
                    ("open_tcp_stream", self.__Backend__open_tcp_stream__mock),
                    ("open_uds_stream", self.__Backend__open_uds_stream__mock),
                )
                for target, mocker in mockers:
                    patcher = asynctest.mock.patch.object(backend, target, mocker)
                    patcher.start()
                    patchers.append(patcher)
            else:
                # 3B. Start patching dispatcher's send()
                target, mocker = "send", self.__Dispatcher__send__mock
                patcher = asynctest.mock.patch.object(dispatch, target, mocker)
                patcher.start()
                patchers.append(patcher)

        try:
            yield partial(self._capture, pattern=pattern)
        finally:
            # 4. Stop patching
            for patcher in patchers:
                patcher.stop()

    async def __Client__send__spy(
        self, client: Client, request: Request, **kwargs: typing.Any
    ) -> Response:
        """
        Spy for Client.send().

        Patches request.url and attaches matched response template,
        and mocks client backend open stream methods.
        """
        with self._patch_backend(client.dispatch, request) as capture:
            try:
                response = None
                response = await _send(client, request, **kwargs)
                return response
            finally:
                capture(request, response)

    async def __Dispatcher__send__mock(
        self, request: Request, **kwargs: typing.Any
    ) -> Response:
        # TODO: Support pass-through
        hostname = request.url.host
        response = getattr(hostname, "attachment", None)  # Pickup attached template
        return await response.build(request)

    async def __Backend__open_tcp_stream__mock(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseSocketStream:
        response = getattr(hostname, "attachment", None)  # Pickup attached template
        return await response.socket_stream()

    async def __Backend__open_uds_stream__mock(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseSocketStream:
        response = getattr(hostname, "attachment", None)  # Pickup attached template
        return await response.socket_stream()
