import io
import ssl
import typing
from contextlib import contextmanager
from functools import partialmethod, wraps

import asynctest
from httpx.client import BaseClient
from httpx.concurrency.base import ConcurrencyBackend
from httpx.config import TimeoutConfig
from httpx.models import AsyncRequest, AsyncResponse, Headers, HeaderTypes

from .models import ContentDataTypes, RequestPattern, ResponseTemplate, URLResponse

# TODO: Remove try-except once httpx.BaseSocketStream is released
try:
    from httpx import BaseSocketStream  # type: ignore
except ImportError:  # pragma: nocover
    from httpx import BaseTCPStream as BaseSocketStream

_get_response = BaseClient._get_response  # Pass-through reference

__all__ = ["HTTPXMock"]


class HTTPXMock:
    def __init__(
        self, assert_all_called: bool = True, assert_all_mocked: bool = True
    ) -> None:
        self._assert_all_called = assert_all_called
        self._assert_all_mocked = assert_all_mocked
        self._patchers: typing.List[asynctest.mock._patch] = []
        self._patterns: typing.List[RequestPattern] = []
        self.aliases: typing.Dict[str, RequestPattern] = {}
        self.calls: typing.List[
            typing.Tuple[AsyncRequest, typing.Optional[AsyncResponse]]
        ] = []

    def clear(self):
        self._patchers.clear()
        self._patterns.clear()
        self.aliases.clear()
        self.calls.clear()

    def __enter__(self) -> "HTTPXMock":
        self.start()
        return self

    def __exit__(self, *args: typing.Any) -> None:
        self.stop()
        if self._assert_all_called:
            self.assert_all_called()
        self.clear()

    def mock(self, func=None):
        """
        Starts mocking and stops once wrapped function, or context, is executed.
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper if func else self

    def start(self) -> None:
        """
        Starts mocking httpx.
        """
        # Unbound -> bound spy version of client._get_response
        async def unbound_get_response(
            client: BaseClient, request: AsyncRequest, **kwargs: typing.Any
        ) -> AsyncResponse:
            return await self._get_response_spy(client, request, **kwargs)

        # Spy on client._get_response
        self._patchers.append(
            asynctest.mock.patch(
                "httpx.client.BaseClient._get_response", new=unbound_get_response
            )
        )

        # Start patching
        for patcher in self._patchers:
            patcher.start()

    def stop(self) -> None:
        """
        Stops mocking httpx.
        """
        while self._patchers:
            patcher = self._patchers.pop()
            patcher.stop()

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
                        'ResponseTemplate or an AsyncResponse, got "{}"'
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

    @contextmanager
    def _patch_backend(
        self,
        backend: ConcurrencyBackend,
        request: AsyncRequest,
        response: typing.Optional[ResponseTemplate],
    ) -> typing.Iterator[None]:
        patchers = []

        if response is not None:
            # 1. Patch request url with response for later pickup in patched backend
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

        # 2. Start patchers
        for patcher in patchers:
            patcher.start()

        try:
            yield
        finally:
            # 3. Stop patchers
            for patcher in patchers:
                patcher.start()

    async def _get_response_spy(
        self, client: BaseClient, request: AsyncRequest, **kwargs: typing.Any
    ) -> AsyncResponse:
        """
        Spy method for BaseClient._get_response().

        Patches request.url and attaches matched response template,
        and mocks client backend open stream methods.
        """
        # 1. Match request against added patterns
        pattern, _response = self._match(request)

        # 2. Patch client's backend and continue to original _get_response
        try:
            with self._patch_backend(client.concurrency_backend, request, _response):
                response = None
                response = await _get_response(client, request, **kwargs)
        finally:
            # 3. Update stats
            if pattern:
                pattern(request, response)
            self.calls.append((request, response))

        return response

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
        response = getattr(hostname, "attachment")  # Pickup attached response template
        return await self._mock_socket_stream(response)

    async def _mock_socket_stream(self, response: ResponseTemplate) -> BaseSocketStream:
        content = response.content
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
