import io
import json as jsonlib
import re
import ssl
import typing
from contextlib import contextmanager
from functools import partial
from unittest import mock

import asynctest
from httpx.client import BaseClient
from httpx.config import TimeoutConfig
from httpx.models import URL, AsyncRequest, Headers

# TODO: Remove try-except once httpx.BaseSocketStream is released
try:
    from httpx import BaseSocketStream
except ImportError:  # pragma: nocover
    from httpx import BaseTCPStream as BaseSocketStream


CRLF = "\r\n"

istype = lambda t, o: isinstance(o, t)
isregex = partial(istype, type(re.compile("")))

defaults = mock.MagicMock(
    version=1.1, status_code=200, headers={"Content-Type": "text/plain"}, content=b""
)

_get_response = BaseClient._get_response  # Pass-through reference


class Hostname(str):
    pass


class MatchedURL(URL):
    pattern = None
    url_kwargs = None

    @property
    def host(self):
        hostname = Hostname(super().host)
        hostname.match = self
        return hostname


class HTTPXMock:
    def __init__(self):
        self.patchers = []
        self.mocks = []
        self.patterns = {}
        self.calls = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()

    def start(self):
        async def unbound_get_response(client, request: AsyncRequest, **kwargs):
            return await self._get_response_spy(client, request, **kwargs)

        # Spy on client._get_response
        self.patchers.append(
            asynctest.mock.patch(
                "httpx.client.BaseClient._get_response", new=unbound_get_response
            )
        )

        # Start patching
        for patcher in self.patchers:
            patcher.start()

    def stop(self):
        """
        Stops mocking httpx.
        """
        while self.patchers:
            patcher = self.patchers.pop()
            patcher.stop()

    def add(
        self,
        method,
        url,
        status_code=None,
        content=None,
        content_type=None,
        headers=None,
        alias=None,
    ):
        """
        Adds a request method and url pattern with given mocked response details.
        """
        headers = Headers(headers)
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

        self.mocks.append(pattern)
        if alias:
            self.patterns[alias] = pattern  # TODO: rename to requests?

        return pattern

    def match(self, request):
        """
        Matches request method and url against added patterns.
        """
        matched_pattern, url_kwargs = None, {}

        # Filter paterns by method
        patterns = filter(lambda pattern: pattern.method == request.method, self.mocks)

        # Match patterns against url
        for pattern in patterns:
            if isregex(pattern.url):
                match = pattern.url.match(str(request.url))
                if match:
                    matched_pattern = pattern
                    url_kwargs = match.groupdict()
                    break

            elif pattern.url == str(request.url):
                matched_pattern = pattern
                break

        if matched_pattern is not None:
            match = MatchedURL(request.url)
            match.pattern = matched_pattern
            match.url_kwargs = url_kwargs
            return match

    async def _get_response_spy(self, client, request: AsyncRequest, **kwargs):
        """
        Spy method for BaseClient._get_response().

        Patches request.url and attaches matched request/response details,
        and mocks client backend open stream methods.
        """
        # Match request against added patterns
        url_match = self.match(request)

        # Patch request url with matched url for later pickup in mocked backend methods
        if url_match:
            request.url = url_match

        # Mock client's backend open_X_stream methods and pass-through to _get_response
        try:
            global _get_response
            with self._patch_backend_streams(client.concurrency_backend):
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

    @contextmanager
    def _patch_backend_streams(self, backend):
        patchers = []

        # Mock open_tcp_stream()
        patchers.append(
            asynctest.mock.patch.object(
                backend, "open_tcp_stream", self.mocked_open_tcp_stream,
            )
        )

        # Mock open_uds_stream()
        # TODO: Remove if-statement once httpx uds support is released
        if hasattr(backend, "open_uds_stream"):  # pragma: nocover
            patchers.append(
                asynctest.mock.patch.object(
                    backend, "open_uds_stream", self.mocked_open_uds_stream,
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

    async def mocked_open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseSocketStream:
        return await self.mocked_open_uds_stream(None, hostname, ssl_context, timeout)

    async def mocked_open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> BaseSocketStream:
        match = getattr(hostname, "match", None)  # Pickup attached match
        return await self.mock_socket_stream(match, timeout)

    async def mock_socket_stream(
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
                content = content(**match.url_kwargs)
            if isinstance(content, (list, dict)):
                content = jsonlib.dumps(content)
                if headers is not None and "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            content = content.encode("utf-8")  # TODO: Respect charset

        # Build headers and apply defaults
        all_headers = Headers(defaults.headers)
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
