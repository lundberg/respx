from types import TracebackType
from typing import TYPE_CHECKING, Any, List, Optional, Type, Union

from httpcore import (
    AsyncByteStream,
    AsyncHTTPTransport,
    SyncByteStream,
    SyncHTTPTransport,
)

from .models import PassThrough, decode_request, encode_response
from .types import URL, AsyncResponse, Headers, RequestHandler, SyncResponse

if TYPE_CHECKING:
    from .router import Router  # pragma: nocover


class MockTransport(SyncHTTPTransport, AsyncHTTPTransport):
    _handler: Optional[RequestHandler]
    _router: Optional["Router"]

    def __init__(
        self,
        *,
        handler: Optional[RequestHandler] = None,
        router: Optional["Router"] = None,
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
        return self._handler or self._router.handler

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

        # Resolve response
        response = self.handler(request)

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

        # Resolve response
        response = self.handler(request)

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


class TryTransport(SyncHTTPTransport, AsyncHTTPTransport):
    def __init__(
        self, transports: List[Union[SyncHTTPTransport, AsyncHTTPTransport]]
    ) -> None:
        self.transports = transports

    def request(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: SyncByteStream = None,
        ext: dict = None,
    ) -> SyncResponse:
        error: Exception = None
        for transport in self.transports:
            try:
                assert isinstance(transport, SyncHTTPTransport)
                return transport.request(method, url, headers, stream, ext)
            except PassThrough as pass_through:
                stream = pass_through.request.stream  # type: ignore
            except AssertionError:
                raise
            except Exception as e:
                error = e
        raise error

    async def arequest(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: AsyncByteStream = None,
        ext: dict = None,
    ) -> AsyncResponse:
        error: Exception = None
        for transport in self.transports:
            try:
                assert isinstance(transport, AsyncHTTPTransport)
                return await transport.arequest(method, url, headers, stream, ext)
            except PassThrough as pass_through:
                stream = pass_through.request.stream  # type: ignore
            except AssertionError:
                raise
            except Exception as e:
                error = e
        raise error
