import asyncio
import io
import json as jsonlib
import re
import ssl
import typing
from functools import partial
from unittest import mock

import asynctest
from httpx.client import BaseClient
from httpx.config import TimeoutConfig
from httpx.models import URL, AsyncRequest, Headers

try:
    from httpx.concurrency.asyncio import SocketStream
except ImportError:
    from httpx.concurrency.asyncio import TCPStream as SocketStream


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
        async def _get_response_spy(zelf, request: AsyncRequest, **kwargs):
            # Match request with added patterns
            url_match = self.match(request)

            # Replace request url with matched url for later pickup in backend
            if url_match:
                request.url = url_match

            # Pass-through
            try:
                global _get_response
                response = None
                response = await _get_response(zelf, request, **kwargs)
            except Exception as e:
                raise e
            finally:
                # Update call stats
                event = url_match.pattern if url_match is not None else mock.MagicMock()
                event(request, response)
                self.calls.append(event.call_args_list[-1])

            return response

        # Patch client._get_response
        self.patchers.append(
            asynctest.mock.patch(
                "httpx.client.BaseClient._get_response", new=_get_response_spy
            )
        )

        # Patch backend.open_uds_stream
        self.patchers.append(
            asynctest.mock.patch(
                "httpx.concurrency.asyncio.AsyncioBackend.open_tcp_stream",
                side_effect=self.mocked_open_tcp_stream,
            )
        )

        # Patch backend.open_uds_stream
        try:
            self.patchers.append(
                asynctest.mock.patch(
                    "httpx.concurrency.asyncio.AsyncioBackend.open_uds_stream",
                    side_effect=self.mocked_open_uds_stream,
                )
            )
        except AttributeError:  # pragma: nocover
            # TODO: Remove try-except once httpx uds support is released
            pass

        # Start patching
        for patcher in self.patchers:
            patcher.start()

    def stop(self):
        # Stop patching
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

    async def mocked_open_tcp_stream(
        self,
        hostname: str,
        port: int,
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ) -> SocketStream:
        return await self.mocked_open_uds_stream(None, hostname, ssl_context, timeout)

    async def mocked_open_uds_stream(
        self,
        path: str,
        hostname: typing.Optional[str],
        ssl_context: typing.Optional[ssl.SSLContext],
        timeout: TimeoutConfig,
    ):
        match = getattr(hostname, "match", None)  # Pickup attached match
        return self.mock_socket_stream(match, timeout)

    def mock_socket_stream(
        self, match: typing.Optional[MatchedURL], timeout: TimeoutConfig
    ):
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

        # Mock stream reader with bytes read from data
        stream_reader = asynctest.mock.Mock(asyncio.StreamReader)
        stream_reader.read.side_effect = io.BytesIO(data).read

        # Mock stream writer
        stream_writer = asynctest.mock.Mock(asyncio.StreamWriter)

        return SocketStream(
            stream_reader=stream_reader, stream_writer=stream_writer, timeout=timeout
        )
