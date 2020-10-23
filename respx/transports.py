from warnings import warn

from httpcore import (
    AsyncByteStream,
    AsyncHTTPTransport,
    SyncByteStream,
    SyncHTTPTransport,
)

from .models import MockResponse, encode_response
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
        request = (method, url, headers, stream)
        mock_response, route = self.match(request)

        try:
            if mock_response is None:
                # Pass-through request
                pass_through = ext.pop("pass_through", None)
                if pass_through is None:
                    raise ValueError("pass_through not supported with manual transport")
                response = pass_through(method, url, headers, stream, ext)
            else:
                if isinstance(mock_response, MockResponse):
                    response = mock_response.raw
                else:
                    response = encode_response(mock_response)
            return response
        except Exception:
            response = None
            raise
        finally:
            self.record(
                request, response, route=route
            )  # pragma: nocover  # python 3.9 bug

    async def arequest(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: AsyncByteStream = None,
        ext: dict = None,
    ) -> AsyncResponse:
        request = (method, url, headers, stream)
        mock_response, route = self.match(request)

        try:
            if mock_response is None:
                # Pass-through request
                pass_through = ext.pop("pass_through", None)
                if pass_through is None:
                    raise ValueError("pass_through not supported with manual transport")
                response = await pass_through(method, url, headers, stream, ext)
            else:
                if isinstance(mock_response, MockResponse):
                    response = await mock_response.araw
                else:
                    response = encode_response(mock_response)

            return response
        except Exception:
            response = None
            raise
        finally:
            self.record(
                request, response, route=route
            )  # pragma: nocover  # python 3.9 bug

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
