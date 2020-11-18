from types import TracebackType
from typing import Any, Optional, Type

from httpcore import (
    AsyncByteStream,
    AsyncHTTPTransport,
    SyncByteStream,
    SyncHTTPTransport,
)

from .models import decode_request, encode_response
from .router import Router
from .types import URL, AsyncResponse, Headers, RequestHandler, SyncResponse


class MockTransport(SyncHTTPTransport, AsyncHTTPTransport):
    _handler: Optional[RequestHandler]
    _router: Optional[Router]

    def __init__(
        self,
        *,
        handler: Optional[RequestHandler] = None,
        router: Optional[Router] = None,
    ):
        if handler and not router:
            self._handler = handler
            self._router = None
        elif router:
            self._router = router
            self._handler = None
        else:
            raise RuntimeError(
                "Missing a MockTransport required handler or router argument"
            )

    @property
    def handler(self) -> RequestHandler:
        return self._handler or self._router.resolve

    def request(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: SyncByteStream = None,
        ext: dict = None,
    ) -> SyncResponse:
        raw_request = (method, url, headers, stream)
        request = decode_request(raw_request)

        # Pre-read request
        request.read()
        stream = request.stream  # type: ignore

        # Resolve response
        response = self.handler(request)
        if response is None:
            raise ValueError("pass_through not supported when using MockTransport")

        raw_response = encode_response(response)
        return raw_response  # type: ignore

    async def arequest(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: AsyncByteStream = None,
        ext: dict = None,
    ) -> AsyncResponse:
        raw_request = (method, url, headers, stream)
        request = decode_request(raw_request)

        # Pre-read request
        await request.aread()
        stream = request.stream  # type: ignore

        # Resolve response
        response = self.handler(request)
        if response is None:
            raise ValueError("pass_through not supported when using MockTransport")

        raw_response = encode_response(response)
        return raw_response  # type: ignore

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        if not exc_type and self._router and self._router._assert_all_called:
            self._router.assert_all_called()

    async def __aexit__(self, *args: Any) -> None:
        self.__exit__(*args)
