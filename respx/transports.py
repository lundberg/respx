from warnings import warn

from httpcore import (
    AsyncByteStream,
    AsyncHTTPTransport,
    SyncByteStream,
    SyncHTTPTransport,
)

from .models import decode_request, encode_response
from .router import Router
from .types import URL, AsyncResponse, Headers, SyncResponse


class BaseMockTransport(Router):
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
        response = self.resolve(request)

        if response is None:
            pass_through = ext.pop("pass_through", None)
            if pass_through is None:
                raise ValueError("pass_through not supported with manual transport")
            raw_response = pass_through(method, url, headers, stream, ext)
        else:
            raw_response = encode_response(response)

        return raw_response

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
        response = self.resolve(request)

        if response is None:
            pass_through = ext.pop("pass_through", None)
            if pass_through is None:
                raise ValueError("pass_through not supported with manual transport")
            raw_response = await pass_through(method, url, headers, stream, ext)
        else:
            raw_response = encode_response(response)

        return raw_response

    def close(self) -> None:
        if self._assert_all_called:
            self.assert_all_called()

    async def aclose(self) -> None:
        self.close()


class SyncMockTransport(BaseMockTransport, SyncHTTPTransport):
    def __init__(self, **kwargs):
        warn(
            "SyncMockTransport is deprecated. Please, use MockTransport",
            category=DeprecationWarning,
        )
        super().__init__(**kwargs)


class AsyncMockTransport(BaseMockTransport, AsyncHTTPTransport):
    def __init__(self, **kwargs):
        warn(
            "SyncMockTransport is deprecated. Please, use MockTransport",
            category=DeprecationWarning,
        )
        super().__init__(**kwargs)
