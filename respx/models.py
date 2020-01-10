import inspect
import io
import json as jsonlib
import re
import typing
from functools import partial
from urllib.parse import urljoin

import asynctest
from httpx import URL, Headers, Request, Response
from httpx.backends.base import BaseSocketStream
from httpx.models import HeaderTypes

Regex = type(re.compile(""))
Kwargs = typing.Dict[str, typing.Any]
URLPatternTypes = typing.Union[str, typing.Pattern[str]]
ContentDataTypes = typing.Union[
    bytes, str, typing.List, typing.Dict, typing.Callable, Exception,
]

istype = lambda t, o: isinstance(o, t)
isregex = partial(istype, Regex)


class ResponseTemplate:
    def __init__(
        self,
        status_code: typing.Optional[int] = None,
        headers: typing.Optional[HeaderTypes] = None,
        content: typing.Optional[ContentDataTypes] = None,
        context: typing.Optional[Kwargs] = None,
    ) -> None:
        self.http_version = 1.1
        self.status_code = status_code or 200
        self.context = context if context is not None else {}
        self._headers = Headers(headers or {})
        self._content = content if content is not None else b""

    def clone(self, context: typing.Optional[Kwargs] = None) -> "ResponseTemplate":
        return ResponseTemplate(
            self.status_code, self._headers, self._content, context=context
        )

    @property
    def headers(self) -> Headers:
        if "Content-Type" not in self._headers:
            self._headers["Content-Type"] = "text/plain"
        return self._headers

    @property
    def content(self) -> bytes:
        return self.encode_content(self._content)

    @content.setter
    def content(self, content: ContentDataTypes) -> None:
        self._content = content

    @property
    async def acontent(self) -> bytes:
        content: ContentDataTypes = self._content

        # Pre-handle async content callbacks
        if callable(content) and inspect.iscoroutinefunction(content):
            content = await content(**self.context)

        return self.encode_content(content)

    def encode_content(self, content: ContentDataTypes) -> bytes:
        if callable(content):
            content = content(**self.context)

        if isinstance(content, Exception):
            raise content

        if isinstance(content, bytes):
            return content

        if isinstance(content, (list, dict)):
            content = jsonlib.dumps(content)
            if "Content-Type" not in self._headers:
                self._headers["Content-Type"] = "application/json"

        assert isinstance(content, str), "Invalid type of content"
        content = content.encode("utf-8")  # TODO: Respect charset

        return content

    def build(
        self, request: Request, content: typing.Optional[bytes] = None
    ) -> Response:
        content = content or self.content
        return Response(
            status_code=self.status_code,
            http_version=f"HTTP/{self.http_version}",
            headers=self.headers,
            content=content,
            request=request,
        )

    async def abuild(self, request: Request) -> Response:
        content = await self.acontent
        return self.build(request, content)

    @property
    async def socket_stream(self) -> BaseSocketStream:
        """
        Mocks a SocketStream with bytes read from generated raw response.
        """
        content = await self.acontent

        # Build raw bytes data
        http_version = f"HTTP/{self.http_version}"
        status_line = f"{http_version} {self.status_code} MOCK"
        lines = [status_line]
        lines.extend([f"{key.title()}: {value}" for key, value in self.headers.items()])

        CRLF = b"\r\n"
        data = CRLF.join((line.encode("ascii") for line in lines))
        data += CRLF * 2
        data += content

        # Mock a SocketStream with bytes read from data
        reader = io.BytesIO(data)
        socket_stream = asynctest.mock.Mock(BaseSocketStream)
        socket_stream.read.side_effect = lambda n, *args, **kwargs: reader.read(n)
        socket_stream.get_http_version.return_value = http_version

        return socket_stream


class RequestPattern:
    def __init__(
        self,
        method: typing.Union[str, typing.Callable],
        url: typing.Optional[URLPatternTypes],
        response: ResponseTemplate,
        pass_through: bool = False,
        alias: typing.Optional[str] = None,
        base_url: typing.Optional[str] = None,
    ) -> None:
        self._match_func: typing.Optional[typing.Callable] = None

        if callable(method):
            self.method = None
            self.url = None
            self.pass_through = None
            self._match_func = method
        else:
            self.method = method
            self.set_url(url, base=base_url)
            self.pass_through = pass_through

        self.response = response
        self.alias = alias
        self.stats = asynctest.mock.MagicMock()

    @property
    def called(self):
        return self.stats.called

    @property
    def call_count(self):
        return self.stats.call_count

    @property
    def calls(self):
        return [
            (request, response) for (request, response), _ in self.stats.call_args_list
        ]

    def get_url(self) -> typing.Optional[URLPatternTypes]:
        return self._url

    def set_url(
        self, url: typing.Optional[URLPatternTypes], base: typing.Optional[str] = None,
    ) -> None:
        url = url or None
        if url is None:
            url = url if base is None else base
        elif isinstance(url, str):
            url = url if base is None else urljoin(base, url)
        elif isregex(url):
            url = url if base is None else re.compile(urljoin(base, url.pattern))
        else:
            raise ValueError(
                "Request url pattern must be str or compiled regex, got {}.".format(
                    type(url).__name__
                )
            )
        self._url = url

    url = property(get_url, set_url)

    def match(
        self, request: Request
    ) -> typing.Optional[typing.Union[Request, ResponseTemplate]]:
        """
        Matches request with configured pattern;
        custom matcher function or http method + url pattern.

        Returns None for a non-matching pattern, mocked response for a match,
        or input request for pass-through.
        """
        matches = False
        url_params: Kwargs = {}

        if self.pass_through:
            return request

        if self._match_func:
            response = self.response.clone(context={"request": request})
            return self._match_func(request, response)

        if self.method != request.method:
            return None

        if not self._url:
            matches = True
        elif isinstance(self._url, str):
            matches = self._url == str(request.url)
        else:
            match = self._url.match(str(request.url))
            if match:
                matches = True
                url_params = match.groupdict()

        if matches:
            return self.response.clone(context={"request": request, **url_params})

        return None


class URLResponse(URL):
    def __init__(self, url: URL, response: ResponseTemplate) -> None:
        self.response = response
        super().__init__(url)

    @property
    def host(self) -> str:
        """
        Returns host (str) with attached pattern match (self)
        """
        hostname = AttachmentString(super().host)
        hostname.attachment = self.response
        return hostname


class AttachmentString(str):
    attachment: typing.Optional[typing.Any] = None
