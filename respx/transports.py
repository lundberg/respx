from types import TracebackType
from typing import TYPE_CHECKING, Any, List, Optional, Type, Union

from httpx import AsyncBaseTransport, AsyncByteStream, BaseTransport, SyncByteStream

from .models import PassThrough, decode_request, encode_response
from .types import (
    URL,
    AsyncRequestHandler,
    AsyncResponse,
    Headers,
    RequestHandler,
    SyncResponse,
)

if TYPE_CHECKING:
    from .router import Router  # pragma: nocover


class MockTransport(BaseTransport, AsyncBaseTransport):
    _handler: Optional[RequestHandler]
    _async_handler: Optional[AsyncRequestHandler]
    _router: Optional["Router"]

    def __init__(
        self,
        *,
        handler: Optional[RequestHandler] = None,
        async_handler: Optional[AsyncRequestHandler] = None,
        router: Optional["Router"] = None,
    ):
        if handler and not router:
            self._router = None
            self._handler = handler
            self._async_handler = async_handler
        elif router:
            self._router = router
            self._handler = None
            self._async_handler = None
        else:
            raise RuntimeError(
                "Missing a MockTransport required handler or router argument"
            )

    @property
    def handler(self) -> RequestHandler:
        return self._handler or self._router.handler

    @property
    def async_handler(self) -> AsyncRequestHandler:
        return self._async_handler or self._router.async_handler

    def handle_request(
        self,
        method: bytes,
        url: URL,
        headers: Headers,
        stream: SyncByteStream,
        extensions: dict,
    ) -> SyncResponse:
        raw_request = (method, url, headers, stream)
        request = decode_request(raw_request)

        # Pre-read request
        request.read()

        # Resolve response
        response = self.handler(request)

        raw_response = encode_response(response)
        return raw_response  # type: ignore

    async def handle_async_request(
        self,
        method: bytes,
        url: URL,
        headers: Headers,
        stream: AsyncByteStream,
        extensions: dict,
    ) -> AsyncResponse:
        raw_request = (method, url, headers, stream)
        request = decode_request(raw_request)

        # Pre-read request
        await request.aread()

        # Resolve response
        response = await self.async_handler(request)

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


class TryTransport(BaseTransport, AsyncBaseTransport):
    def __init__(
        self, transports: List[Union[BaseTransport, AsyncBaseTransport]]
    ) -> None:
        self.transports = transports

    def handle_request(
        self,
        method: bytes,
        url: URL,
        headers: Headers,
        stream: SyncByteStream,
        extensions: dict,
    ) -> SyncResponse:
        for transport in self.transports:
            try:
                assert isinstance(transport, BaseTransport)
                return transport.handle_request(
                    method, url, headers, stream, extensions
                )
            except PassThrough as pass_through:
                stream = pass_through.request.stream  # type: ignore

        raise RuntimeError()  # pragma: nocover

    async def handle_async_request(
        self,
        method: bytes,
        url: URL,
        headers: Headers,
        stream: AsyncByteStream,
        extensions: dict,
    ) -> AsyncResponse:
        for transport in self.transports:
            try:
                assert isinstance(transport, AsyncBaseTransport)
                return await transport.handle_async_request(
                    method, url, headers, stream, extensions
                )
            except PassThrough as pass_through:
                stream = pass_through.request.stream  # type: ignore

        raise RuntimeError()  # pragma: nocover
