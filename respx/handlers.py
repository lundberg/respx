from typing import Any, Callable

import httpx


class TransportHandler:
    def __init__(self, transport: httpx.BaseTransport) -> None:
        self.transport = transport

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if not isinstance(request.stream, httpx.SyncByteStream):  # pragma: nocover
            raise RuntimeError("Attempted to route an async request to a sync app.")

        (status_code, headers, stream, extensions) = self.transport.handle_request(
            request.method.encode(),
            request.url.raw,
            headers=request.headers.raw,
            stream=request.stream,
            extensions={},
        )
        return httpx.Response(
            status_code,
            headers=headers,
            stream=stream,
            extensions=extensions,
            request=request,
        )


class AsyncTransportHandler:
    def __init__(self, transport: httpx.AsyncBaseTransport) -> None:
        self.transport = transport

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        if not isinstance(request.stream, httpx.AsyncByteStream):  # pragma: nocover
            raise RuntimeError("Attempted to route a sync request to an async app.")

        (
            status_code,
            headers,
            stream,
            extensions,
        ) = await self.transport.handle_async_request(
            request.method.encode(),
            request.url.raw,
            headers=request.headers.raw,
            stream=request.stream,
            extensions={},
        )
        return httpx.Response(
            status_code,
            headers=headers,
            stream=stream,
            extensions=extensions,
            request=request,
        )


class WSGIHandler(TransportHandler):
    def __init__(self, app: Callable, **kwargs: Any) -> None:
        super().__init__(httpx.WSGITransport(app=app, **kwargs))


class ASGIHandler(AsyncTransportHandler):
    def __init__(self, app: Callable, **kwargs: Any) -> None:
        super().__init__(httpx.ASGITransport(app=app, **kwargs))
