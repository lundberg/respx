import io
import json as jsonlib
import re
import ssl
import typing
from contextlib import contextmanager
from functools import partial, wraps
from unittest import mock

import asynctest
from httpx.client import BaseClient
from httpx.concurrency.base import ConcurrencyBackend
from httpx.config import TimeoutConfig
from httpx.models import URL, AsyncRequest, AsyncResponse, Headers, HeaderTypes

# TODO: Remove try-except once httpx.BaseSocketStream is released
try:
    from httpx import BaseSocketStream  # type: ignore
except ImportError:  # pragma: nocover
    from httpx import BaseTCPStream as BaseSocketStream


Regex = type(re.compile(""))
URLParams = typing.Dict[str, typing.Any]
ContentDataTypes = typing.Union[bytes, str, typing.List, typing.Dict, typing.Callable]

istype = lambda t, o: isinstance(o, t)
isregex = partial(istype, Regex)

CRLF = "\r\n"

defaults = mock.MagicMock(
    version=1.1, status_code=200, headers={"Content-Type": "text/plain"}, content=b""
)

_get_response = BaseClient._get_response  # Pass-through reference


class MatchedURL(URL):
    def __init__(
        self, url: URL, url_params: URLParams, pattern: mock.MagicMock
    ) -> None:
        super().__init__(url)
        self.url_params = url_params
        self.pattern = pattern

    @property
    def host(self) -> "Hostname":
        """
        Returns host (str) with attached pattern match (self)
        """
        hostname = Hostname(super().host)
        hostname.match = self
        return hostname


class Hostname(str):
    match: typing.Optional[MatchedURL] = None


class HTTPXMock:
    def __init__(self):
        self.clear()

    def clear(self):
        self._patchers = []
        self._patterns = []
        self.aliases = {}
        self.calls = []

    def __enter__(self) -> "HTTPXMock":
        self.start()
        return self

    def __exit__(self, *args: typing.Any) -> None:
        self.stop()

    def activate(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper

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
        method: str,
        url: typing.Union[str, typing.Pattern],
        status_code: typing.Optional[int] = None,
        content: typing.Optional[ContentDataTypes] = None,
        content_type: typing.Optional[str] = None,
        headers: typing.Optional[HeaderTypes] = None,
        alias: typing.Optional[str] = None,
    ) -> mock.MagicMock:
        """
        Adds a request pattern and given mocked response details.
        """
        headers = Headers(headers or {})
        if content_type:
            headers["Content-Type"] = content_type

        pattern = mock.MagicMock(
            method=method,
            url=url,
            response=mock.MagicMock(
                version=defaults.version,
                status_code=status_code or defaults.status_code,
                headers=headers,
                content=content if content is not None else defaults.content,
            ),
        )

        self._patterns.append(pattern)
        if alias:
            self.aliases[alias] = pattern

        return pattern

    def __getitem__(self, alias: str) -> typing.Optional[mock.MagicMock]:
        return self.aliases.get(alias)

    def _match(self, request: AsyncRequest) -> typing.Optional[MatchedURL]:
        """
        Matches request method and url against added patterns.
        """
        matched_pattern = None
        url_params: URLParams = {}

        # Filter paterns by method
        patterns = filter(lambda p: p.method == request.method, self._patterns)

        # Match patterns against url
        for pattern in patterns:
            if isregex(pattern.url):
                match = pattern.url.match(str(request.url))
                if match:
                    matched_pattern = pattern
                    url_params = match.groupdict()
                    break

            elif pattern.url == str(request.url):
                matched_pattern = pattern
                break

        if matched_pattern is not None:
            return MatchedURL(request.url, url_params, matched_pattern)

        return None

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

        Patches request.url and attaches matched request/response details,
        and mocks client backend open stream methods.
        """
        # Match request against added patterns
        url_match = self._match(request)

        # Patch request url with matched url for later pickup in mocked backend methods
        if url_match:
            request.url = url_match

        # Mock client's backend open_X_stream methods and pass-through to _get_response
        try:
            global _get_response
            with self._patch_backend(client.concurrency_backend):
                response = None
                response = await _get_response(client, request, **kwargs)
        except Exception as e:
            raise e
        finally:
            # Update call stats
            event = url_match.pattern if url_match is not None else mock.MagicMock()
            event(request, response)
            self.calls.append(event.call_args_list[-1])

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
        match = getattr(hostname, "match", None)  # Pickup attached match
        return await self._mock_socket_stream(match, timeout)

    async def _mock_socket_stream(
        self, match: typing.Optional[MatchedURL], timeout: TimeoutConfig
    ) -> BaseSocketStream:
        if match is None:
            version = defaults.version
            status_code = defaults.status_code
            headers = None
            content = defaults.content
        else:
            template = match.pattern.response
            version = template.version
            status_code = template.status_code
            headers = template.headers
            content = template.content

        # Build and encode content
        if not isinstance(content, bytes):
            if isinstance(content, Exception):
                raise content
            if callable(content):
                content = content(**(match.url_params if match is not None else {}))
            if isinstance(content, (list, dict)):
                content = jsonlib.dumps(content)
                if headers is not None and "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            content = content.encode("utf-8")  # TODO: Respect charset

        # Build headers and apply defaults
        all_headers = Headers(defaults.headers)
        if headers:
            all_headers.update(headers)

        # Build raw bytes data
        http_version = f"HTTP/{version}"
        status_line = f"{http_version} {status_code} MOCK"  # TODO: Handle http version
        lines = [status_line]
        lines.extend([f"{key.title()}: {value}" for key, value in all_headers.items()])
        data = CRLF.join(lines).encode("ascii")
        data += CRLF.encode("ascii") * 2
        data += content

        # Mock backend SocketStream with bytes read from data
        reader = io.BytesIO(data)
        socket_stream = asynctest.mock.Mock(BaseSocketStream)
        socket_stream.read.side_effect = lambda n, *args, **kwargs: reader.read(n)
        socket_stream.get_http_version.return_value = http_version

        return socket_stream
