import json as jsonlib
import re
import typing
from functools import partial
from unittest import mock

from httpx.models import URL, AsyncRequest, AsyncResponse, Headers, HeaderTypes

Regex = type(re.compile(""))
Kwargs = typing.Dict[str, typing.Any]
ContentDataTypes = typing.Union[bytes, str, typing.List, typing.Dict, typing.Callable]

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
        headers = Headers({"Content-Type": "text/plain"})
        if self._headers:
            headers.update(self._headers)
        return headers

    def get_content(self) -> bytes:
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

    def set_content(self, content: ContentDataTypes) -> None:
        self._content = content

    content = property(get_content, set_content)

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
        alias: typing.Optional[str] = None,
    ) -> None:
        self.method = method
        self.url = url
        self.response = response
        self.alias = alias

        self._match_func = method if callable(method) else None
        self._stats = mock.MagicMock()

    @property
    def called(self):
        return self._stats.called

    @property
    def calls(self):
        return [
            (request, response) for (request, response), _ in self._stats.call_args_list
        ]

    def __call__(
        self, request: AsyncRequest, response: typing.Optional[AsyncResponse]
    ) -> None:
        self._stats(request, response)

    def match(self, request: AsyncRequest) -> typing.Optional[ResponseTemplate]:
        matches = False
        url_params: Kwargs = {}

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
                raise ValueError("Request url pattern must be str or compiled regex")

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
