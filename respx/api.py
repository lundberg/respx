import inspect
import ssl
import typing
from contextlib import contextmanager
from functools import partial, partialmethod, wraps

import asynctest
from httpx import AsyncClient, Client, Timeout
from httpx.backends.base import BaseSocketStream, ConcurrencyBackend
from httpx.dispatch.base import AsyncDispatcher, SyncDispatcher
from httpx.models import Headers, HeaderTypes, Request, Response

from .models import ContentDataTypes, RequestPattern, ResponseTemplate, URLResponse

__all__ = ["HTTPXMock"]

# Pass-through references
_Client__send = Client.send
_AsyncClient__send = AsyncClient.send


class HTTPXMock:
    def __init__(
        self,
        assert_all_called: bool = True,
        assert_all_mocked: bool = True,
        base_url: typing.Optional[str] = None,
        proxy: typing.Optional["HTTPXMock"] = None,
    ) -> None:
        self._assert_all_called = assert_all_called
        self._assert_all_mocked = assert_all_mocked
        self._base_url = base_url
        self._proxy = proxy
        self._mocks: typing.List[HTTPXMock] = []
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
            # Parantheses used, branch out to new nested instance.
            # - Only stage when using local ctx `with respx.mock(...) as httpx_mock:`
            # - First stage when using local decorator `@respx.mock(...)`
            #   FYI, global ctx `with respx.mock:` hits __enter__ directly
            settings: typing.Dict[str, typing.Any] = {
                "base_url": base_url,
                "proxy": self,
            }
            if assert_all_called is not None:
                settings["assert_all_called"] = assert_all_called
            if assert_all_mocked is not None:
                settings["assert_all_mocked"] = assert_all_mocked
            return self.__class__(**settings)

        # Async Decorator
        @wraps(func)
        async def async_decorator(*args, **kwargs):
            assert func is not None
            if self._proxy:
                kwargs["httpx_mock"] = self
            async with self:
                return await func(*args, **kwargs)

        # Sync Decorator
        @wraps(func)
        def sync_decorator(*args, **kwargs):
            assert func is not None
            if self._proxy:
                kwargs["httpx_mock"] = self
            with self:
                return func(*args, **kwargs)

        # Dispatch async/sync decorator, depening on decorated function.
        # - Only stage when using global decorator `@respx.mock`
        # - Second stage when using local decorator `@respx.mock(...)`
        return async_decorator if inspect.iscoroutinefunction(func) else sync_decorator

    def __enter__(self) -> "HTTPXMock":
        self.start()
        return self

    def __exit__(self, *args: typing.Any) -> None:
        self.stop()

    async def __aenter__(self) -> "HTTPXMock":
        return self.__enter__()

    async def __aexit__(self, *args: typing.Any) -> None:
        self.__exit__(*args)

    def start(self) -> None:
        """
        Register mock/patterns and starts patching HTTPX.
        """
        self._register(self)

    def stop(self, clear: bool = True, reset: bool = True) -> None:
        """
        Unregister mock/patterns and stop patching HTTPX, when no registered mocks left.
        """
        try:
            if self._assert_all_called:
                self.assert_all_called()
        finally:
            if clear:
                self.clear()
            if reset:
                self.reset()

            self._unregister(self)

    def _register(self, httpx_mock: "HTTPXMock") -> None:
        # Ensure we patch HTTPX using proxy instance
        if self._proxy:
            self._proxy._register(httpx_mock)
            return

        # Register given mock instance / patterns
        self._mocks.append(httpx_mock)
        self._patch()

    def _unregister(self, httpx_mock: "HTTPXMock") -> None:
        # Ensure we unpatch HTTPX using proxy instance
        if self._proxy is not None:
            self._proxy._unregister(httpx_mock)
            return

        # Unregister given mock instance / patterns
        assert httpx_mock in self._mocks, "HTTPX mock already stopped!"
        self._mocks.remove(httpx_mock)
        self._unpatch()

    def _patch(self) -> None:
        # Ensure we only patch HTTPX once!
        if self._patchers:
            return

        # Unbound -> bound spy version of Client.send
        def unbound_sync_send(
            client: Client, request: Request, **kwargs: typing.Any
        ) -> Response:
            return self.__Client__send__spy(client, request, **kwargs)

        # Unbound -> bound spy version of AsyncClient.send
        async def unbound_async_send(
            client: AsyncClient, request: Request, **kwargs: typing.Any
        ) -> Response:
            return await self.__AsyncClient__send__spy(client, request, **kwargs)

        # Start patching HTTPX
        mockers = (
            ("httpx.Client.send", unbound_sync_send),
            ("httpx.AsyncClient.send", unbound_async_send),
        )
        for target, mocker in mockers:
            patcher = asynctest.mock.patch(target, new=mocker)
            patcher.start()
            self._patchers.append(patcher)

    def _unpatch(self) -> None:
        # Ensure we don't stop patching HTTPX when registered mocks exists
        if self._mocks:
            return

        # Stop patching HTTPX
        while self._patchers:
            patcher = self._patchers.pop()
            patcher.stop()

    def clear(self) -> None:
        """
        Clears added patterns and aliases.
        """
        self._patterns.clear()
        self.aliases.clear()

    def reset(self) -> None:
        """
        Resets call stats.
        """
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
        "HTTPXMock", typing.Optional[RequestPattern], typing.Optional[ResponseTemplate]
    ]:
        matched_pattern: typing.Optional[RequestPattern] = None
        matched_pattern_index: typing.Optional[int] = None
        response: typing.Optional[ResponseTemplate] = None
        # if request.url == "https://foo.bar/asgi/":
        # import pdb; pdb.set_trace()

        # Iterate all started mockers and their patterns
        for httpx_mock in self._mocks:
            patterns = httpx_mock._patterns

            for i, pattern in enumerate(patterns):
                match = pattern.match(request)
                if not match:
                    continue

                if matched_pattern_index is not None:
                    # Multiple matches found, drop and use the first one
                    patterns.pop(matched_pattern_index)
                    break

                used_mock = httpx_mock
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

            if matched_pattern:
                break

        if matched_pattern is None:
            # Assert we always get a pattern match, if check is enabled
            allows_unmocked = tuple(m for m in self._mocks if not m._assert_all_mocked)
            assert allows_unmocked, f"RESPX: {request!r} not mocked!"

            # Relate default response to first mocker that allows unmocked requests
            used_mock = allows_unmocked[0]
            response = ResponseTemplate()

        return used_mock, matched_pattern, response

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
    def _patch_dispatcher(
        self, dispatch: typing.Union[SyncDispatcher, AsyncDispatcher], request: Request
    ) -> typing.Iterator[typing.Callable]:
        patchers = []

        # 1. Match request against added patterns
        httpx_mock, pattern, response = self._match(request)

        if response is not None:
            # 2. Patch request url with response for later pickup in patched dispatcher
            request.url = URLResponse(request.url, response)

            backend = getattr(dispatch, "backend", None)
            if isinstance(backend, ConcurrencyBackend):
                # 3A. Concurrency dispatcher -> Patch backend streams
                mockers: typing.List[typing.Tuple[typing.Any, str, typing.Callable]] = [
                    (backend, "open_tcp_stream", self.__Backend__open_tcp_stream__mock),
                    (backend, "open_uds_stream", self.__Backend__open_uds_stream__mock),
                ]
            elif isinstance(dispatch, SyncDispatcher):
                # 3B. Synchronous dispatcher -> Patch send()
                mockers = [(dispatch, "send", self.__SyncDispatcher__send__mock)]
            else:
                # 3C. Asyncronous dispatcher -> Patch send()
                mockers = [(dispatch, "send", self.__AsyncDispatcher__send__mock)]

            for obj, target, mocker in mockers:
                patcher = asynctest.mock.patch.object(obj, target, mocker)
                patcher.start()
                patchers.append(patcher)

        try:
            yield partial(httpx_mock._capture, pattern=pattern)
        finally:
            # 4. Stop patching
            for patcher in patchers:
                patcher.stop()

    def __Client__send__spy(
        self, client: Client, request: Request, **kwargs: typing.Any
    ) -> Response:
        """
        Spy for Client.send().

        Patches request.url and attaches matched response template,
        and mocks client dispatcher send method.
        """
        with self._patch_dispatcher(client.dispatch, request) as capture:
            try:
                response = None
                response = _Client__send(client, request, **kwargs)
                return response
            finally:
                capture(request, response)

    async def __AsyncClient__send__spy(
        self, client: AsyncClient, request: Request, **kwargs: typing.Any
    ) -> Response:
        """
        Spy for AsyncClient.send().

        Patches request.url and attaches matched response template,
        and mocks client concurrency backend open stream methods.
        """
        with self._patch_dispatcher(client.dispatch, request) as capture:
            try:
                response = None
                response = await _AsyncClient__send(client, request, **kwargs)
                return response
            finally:
                capture(request, response)

    def __SyncDispatcher__send__mock(
        self, request: Request, **kwargs: typing.Any
    ) -> Response:
        hostname = request.url.host
        response = getattr(hostname, "attachment", None)  # Pickup attached template
        return response.build(request)

    async def __AsyncDispatcher__send__mock(
        self, request: Request, **kwargs: typing.Any
    ) -> Response:
        hostname = request.url.host
        response = getattr(hostname, "attachment", None)  # Pickup attached template
        return await response.abuild(request)

    async def __Backend__open_tcp_stream__mock(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> BaseSocketStream:
        response = getattr(hostname, "attachment", None)  # Pickup attached template
        return await response.socket_stream

    async def __Backend__open_uds_stream__mock(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: Timeout,
    ) -> BaseSocketStream:
        response = getattr(hostname, "attachment", None)  # Pickup attached template
        return await response.socket_stream
