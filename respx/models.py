import json as jsonlib
import re
import typing
from functools import partial

import asynctest
from httpx.models import URL, AsyncRequest, Headers, HeaderTypes

Regex = type(re.compile(""))
Kwargs = typing.Dict[str, typing.Any]
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

    @property
    def headers(self) -> Headers:
        if "Content-Type" not in self._headers:
            self._headers["Content-Type"] = "text/plain"
        return self._headers

    @property
    def content(self) -> bytes:
        content = self._content

        if isinstance(content, Exception):
            raise content

        if isinstance(content, bytes):
            return content

        if callable(content):
            content = content(**self.context)

        if isinstance(content, (list, dict)):
            content = jsonlib.dumps(content)
            if "Content-Type" not in self._headers:
                self._headers["Content-Type"] = "application/json"

        assert isinstance(content, str), "Invalid type of content"
        content = content.encode("utf-8")  # TODO: Respect charset

        return content

    @content.setter
    def content(self, content: ContentDataTypes) -> None:
        self._content = content

    def clone(self, context: typing.Optional[Kwargs] = None) -> "ResponseTemplate":
        return ResponseTemplate(
            self.status_code, self._headers, self._content, context=context
        )


class RequestPattern:
    def __init__(
        self,
        method: typing.Union[str, typing.Callable],
        url: typing.Optional[typing.Union[str, typing.Pattern]],
        response: ResponseTemplate,
        pass_through: bool = False,
        alias: typing.Optional[str] = None,
    ) -> None:
        self._match_func: typing.Optional[typing.Callable] = None

        if callable(method):
            self.method = None
            self.url = None
            self.pass_through = None
            self._match_func = method
        else:
            self.method = method
            self.url = url
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

    def match(
        self, request: AsyncRequest
    ) -> typing.Optional[typing.Union[AsyncRequest, ResponseTemplate]]:
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

        if self.method == request.method and self.url:
            if isinstance(self.url, str):
                matches = self.url == str(request.url)
            elif isregex(self.url):
                match = self.url.match(str(request.url))
                if match:
                    matches = True
                    url_params = match.groupdict()
            else:
                raise ValueError(
                    "Request url pattern must be str or compiled regex, got {}.".format(
                        type(self.url).__name__
                    )
                )

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
