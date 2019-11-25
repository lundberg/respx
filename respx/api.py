import inspect
import io
import ssl
import typing
from contextlib import contextmanager
from functools import partial, partialmethod, wraps

import asynctest
from httpx import AsyncClient, Client
from httpx.client import BaseClient
from httpx.concurrency.base import ConcurrencyBackend
from httpx.config import TimeoutConfig
from httpx.models import (
    AsyncRequest,
    AsyncResponse,
    BaseResponse,
    Headers,
    HeaderTypes,
    Response,
)

from .models import ContentDataTypes, RequestPattern, ResponseTemplate, URLResponse

# TODO: Remove try-except once httpx.BaseSocketStream is released
try:
    from httpx import BaseSocketStream  # type: ignore
except ImportError:  # pragma: nocover
    from httpx import BaseTCPStream as BaseSocketStream

_get_response = BaseClient._get_response  # Pass-through reference
_send = Client.send  # Pass-through reference
_async_send = AsyncClient.send  # Pass-through reference

__all__ = ["HTTPXMock"]


class HTTPXMock:
    def __init__(
        self,
        assert_all_called: bool = True,
        assert_all_mocked: bool = True,
        local: bool = True,
    ) -> None:
        self._is_local = local
        self._assert_all_called = assert_all_called
        self._assert_all_mocked = assert_all_mocked
        self._patchers: typing.List[asynctest.mock._patch] = []
        self._patterns: typing.List[RequestPattern] = []
        self.aliases: typing.Dict[str, RequestPattern] = {}
        self.stats = asynctest.mock.MagicMock()
        self.calls: typing.List[
            typing.Tuple[AsyncRequest, typing.Optional[BaseResponse]]
        ] = []

    def __call__(
        self,
        func: typing.Optional[typing.Callable] = None,
        assert_all_called: typing.Optional[bool] = None,
        assert_all_mocked: typing.Optional[bool] = None,
    ):
        """
        Decorator or Context Manager.

        Use decorator/manager with parentheses for local state, or without parentheses
        for global state, i.e. shared patterns added outside of scope.
        """
        if func is None:
            # A. First stage of "local" decorator, WITH parentheses.
            # B. Only stage of "local" context manager, WITH parentheses,
            #    "global" context maanager hits __enter__ directly.
            settings = {}
            if assert_all_called is not None:
                settings["assert_all_called"] = assert_all_called
            if assert_all_mocked is not None:
                settings["assert_all_mocked"] = assert_all_mocked
            return self.__class__(**settings)

        # Async Decorator
        @wraps(func)
        async def async_decorator(*args, **kwargs):
            if self._is_local:
                kwargs["httpx_mock"] = self
            async with self:
                return await func(*args, **kwargs)

        # Sync Decorator
        @wraps(func)
        def sync_decorator(*args, **kwargs):
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
        # Unbound -> bound spy version of AsyncClient.send
        async def unbound_async_send(
            client: AsyncClient, request: AsyncRequest, **kwargs: typing.Any
        ) -> AsyncResponse:
            return await self._async_send_spy(client, request, **kwargs)

        # Unbound -> bound spy version of Client.send
        def unbound_send(
            client: Client, request: AsyncRequest, **kwargs: typing.Any
        ) -> Response:
            return self._sync_send_spy(client, request, **kwargs)

        # Start patching
        mockers = (
            ("httpx.client.AsyncClient.send", unbound_async_send),
            ("httpx.client.Client.send", unbound_send),
        )
        for target, mocker in mockers:
            patcher = asynctest.mock.patch(target, new=mocker)
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
        Creates and adds a request pattern with given mocked response details.
        """
        headers = Headers(headers or {})
        if content_type:
            headers["Content-Type"] = content_type

        response = ResponseTemplate(status_code, headers, content)
        pattern = RequestPattern(
            method, url, response, pass_through=pass_through, alias=alias
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
        self, request: AsyncRequest
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
            elif isinstance(match, AsyncRequest):
                # Pass-through request
                response = None
            else:
                raise ValueError(
                    (
                        "Matched request pattern must return either a "
                        'ResponseTemplate or an AsyncRequest, got "{}"'
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
        request: AsyncRequest,
        response: typing.Optional[BaseResponse],
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
        self, backend: ConcurrencyBackend, request: AsyncRequest,
    ) -> typing.Iterator[typing.Callable]:
        patchers = []

        # 1. Match request against added patterns
        pattern, response = self._match(request)

        if response is not None:
            # 2. Patch request url with response for later pickup in patched backend
            request.url = URLResponse(request.url, response)

            # Mock open_tcp_stream()
            patchers.append(
                asynctest.mock.patch.object(
                    backend, "open_tcp_stream", self._open_tcp_stream_mock
                )
            )

            # Mock open_uds_stream()
            # TODO: Remove if-statement once httpx uds support is released
            if hasattr(backend, "open_uds_stream"):  # pragma: nocover
                patchers.append(
                    asynctest.mock.patch.object(
                        backend, "open_uds_stream", self._open_uds_stream_mock
                    )
                )

            # 3. Start patchers
            for patcher in patchers:
                patcher.start()

        try:
            yield partial(self._capture, pattern=pattern)
        finally:
            # 4. Stop patchers
            for patcher in patchers:
                patcher.stop()

    async def _async_send_spy(
        self, client: AsyncClient, request: AsyncRequest, **kwargs: typing.Any
    ) -> AsyncResponse:
        """
        Spy for async AsyncClient.send().

        Patches request.url and attaches matched response template,
        and mocks client backend open stream methods.
        """
        with self._patch_backend(client.concurrency_backend, request) as capture:
            try:
                response = None
                response = await _async_send(client, request, **kwargs)
                return response
            finally:
                capture(request, response)

    def _sync_send_spy(
        self, client: Client, request: AsyncRequest, **kwargs: typing.Any
    ) -> Response:
        """
        Spy for sync Client.send().

        Patches request.url and attaches matched response template,
        and mocks client backend open stream methods.
        """
        with self._patch_backend(client.concurrency_backend, request) as capture:
            try:
                response = None
                response = _send(client, request, **kwargs)
                return response
            finally:
                capture(request, response)

    async def _open_tcp_stream_mock(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseSocketStream:
        return await self._open_uds_stream_mock("", hostname, ssl_context, timeout)

    async def _open_uds_stream_mock(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseSocketStream:
        response = getattr(hostname, "attachment", None)  # Pickup attached response
        return await self._mock_socket_stream(response)

    async def _mock_socket_stream(self, response: ResponseTemplate) -> BaseSocketStream:
        content = await response.content
        headers = response.headers

        # Build raw bytes data
        http_version = f"HTTP/{response.http_version}"
        status_line = f"{http_version} {response.status_code} MOCK"
        lines = [status_line]
        lines.extend([f"{key.title()}: {value}" for key, value in headers.items()])

        CRLF = b"\r\n"
        data = CRLF.join((line.encode("ascii") for line in lines))
        data += CRLF * 2
        data += content

        # Mock backend SocketStream with bytes read from data
        reader = io.BytesIO(data)
        socket_stream = asynctest.mock.Mock(BaseSocketStream)
        socket_stream.read.side_effect = lambda n, *args, **kwargs: reader.read(n)
        socket_stream.get_http_version.return_value = http_version

        return socket_stream
