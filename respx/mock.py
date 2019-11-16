import io
import ssl
import typing
from contextlib import contextmanager
from functools import wraps

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


class HTTPXMock:
    def __init__(self):
        self._patchers = []
        self._patterns = []
        self.aliases = {}
        self.calls = []

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

    def activate(self, func=None):
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
        self.clear()

    def add(
        self,
        method: typing.Union[str, typing.Callable],
        url: typing.Optional[typing.Union[str, typing.Pattern]] = None,
        status_code: typing.Optional[int] = None,
        content: typing.Optional[ContentDataTypes] = None,
        content_type: typing.Optional[str] = None,
        headers: typing.Optional[HeaderTypes] = None,
        alias: typing.Optional[str] = None,
    ) -> RequestPattern:
        """
        Adds a request pattern and given mocked response details.
        """
        headers = Headers(headers or {})
        if content_type:
            headers["Content-Type"] = content_type

        response = ResponseTemplate(status_code, headers, content)
        pattern = RequestPattern(method, url, response, alias=alias)

        self._patterns.append(pattern)
        if alias:
            self.aliases[alias] = pattern

        return pattern

    def __getitem__(self, alias: str) -> typing.Optional[RequestPattern]:
        return self.aliases.get(alias)

    def _match(
        self, request: AsyncRequest
    ) -> typing.Tuple[
        typing.Optional[RequestPattern], typing.Optional[ResponseTemplate]
    ]:
        found_index: typing.Optional[int] = None
        matched_pattern: typing.Optional[RequestPattern] = None
        matched_response: typing.Optional[ResponseTemplate] = None

        for i, pattern in enumerate(self._patterns):
            response = pattern.match(request)
            if not response:
                continue

            if found_index is not None:
                # Multiple matches found, drop and use the first one
                self._patterns.pop(found_index)
                break

            found_index = i
            matched_pattern = pattern
            matched_response = response

        return matched_pattern, matched_response

    @contextmanager
    def _patch_backend(self, backend: ConcurrencyBackend) -> typing.Iterator[None]:
        patchers = []

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

        # Start patchers
        for patcher in patchers:
            patcher.start()

        try:
            yield
        finally:
            # Stop patchers
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
        pattern, template = self._match(request)

        # 2. Patch request url with response for later pickup in mocked backend methods
        request.url = URLResponse(request.url, template or ResponseTemplate())

        # 3. Patch client's backend and pass-through to _get_response
        try:
            global _get_response
            with self._patch_backend(client.concurrency_backend):
                response = None
                response = await _get_response(client, request, **kwargs)
        except Exception as e:
            raise e
        finally:
            # 4. Update stats
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
