import warnings
from typing import Any, Callable, Coroutine, Dict, List, Optional, Pattern, Tuple, Union

import asynctest
from httpcore import (
    AsyncByteStream,
    AsyncHTTPTransport,
    SyncByteStream,
    SyncHTTPTransport,
)

from .models import (
    URL,
    ContentDataTypes,
    Headers,
    HeaderTypes,
    Request,
    RequestPattern,
    Response,
    ResponseTemplate,
    TimeoutDict,
    build_request,
    build_response,
)


class BaseMockTransport:
    def __init__(
        self,
        assert_all_called: bool = True,
        assert_all_mocked: bool = True,
        base_url: Optional[str] = None,
    ) -> None:
        self._assert_all_called = assert_all_called
        self._assert_all_mocked = assert_all_mocked
        self._base_url = base_url

        self.patterns: List[RequestPattern] = []
        self.aliases: Dict[str, RequestPattern] = {}

        self.stats = asynctest.mock.MagicMock()
        self.calls: List[Tuple[Request, Optional[Response]]] = []

    def clear(self):
        """
        Clear added patterns.
        """
        self.patterns.clear()
        self.aliases.clear()

    def reset(self) -> None:
        """
        Resets call stats.
        """
        self.calls.clear()
        self.stats.reset_mock()
        for pattern in self.patterns:
            pattern.stats.reset_mock()

    def __getitem__(self, alias: str) -> Optional[RequestPattern]:
        return self.aliases.get(alias)

    def add(
        self,
        method: Union[str, Callable, RequestPattern],
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        """
        Adds a request pattern with given mocked response details.
        """
        if isinstance(method, RequestPattern):
            pattern = method

        else:
            response = ResponseTemplate(
                status_code, headers, content, content_type=content_type
            )
            pattern = RequestPattern(
                method,
                url,
                response,
                pass_through=pass_through,
                alias=alias,
                base_url=self._base_url,
            )

        self.patterns.append(pattern)
        if pattern.alias:
            self.aliases[pattern.alias] = pattern

        return pattern

    def get(
        self,
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "GET",
            url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
            headers=headers,
            pass_through=pass_through,
            alias=alias,
        )

    def post(
        self,
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "POST",
            url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
            headers=headers,
            pass_through=pass_through,
            alias=alias,
        )

    def put(
        self,
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "PUT",
            url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
            headers=headers,
            pass_through=pass_through,
            alias=alias,
        )

    def patch(
        self,
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "PATCH",
            url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
            headers=headers,
            pass_through=pass_through,
            alias=alias,
        )

    def delete(
        self,
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "DELETE",
            url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
            headers=headers,
            pass_through=pass_through,
            alias=alias,
        )

    def head(
        self,
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "HEAD",
            url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
            headers=headers,
            pass_through=pass_through,
            alias=alias,
        )

    def options(
        self,
        url: Optional[Union[str, Pattern]] = None,
        status_code: Optional[int] = None,
        content: Optional[ContentDataTypes] = None,
        content_type: Optional[str] = None,
        headers: Optional[HeaderTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "OPTIONS",
            url=url,
            status_code=status_code,
            content=content,
            content_type=content_type,
            headers=headers,
            pass_through=pass_through,
            alias=alias,
        )

    def request(self, *args: Any, **kwargs: Any) -> RequestPattern:
        warnings.warn(
            "respx.request() is due to be deprecated. Use respx.add() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.add(*args, **kwargs)

    def record(
        self,
        request: Any,
        response: Optional[Any],
        pattern: Optional[RequestPattern] = None,
    ) -> None:
        request = build_request(request)
        response = build_response(response, request=request)

        if pattern:
            pattern.stats(request, response)

        self.stats(request, response)

        # Copy stats due to unwanted use of property refs in the high-level api
        self.calls[:] = (
            (request, response) for (request, response), _ in self.stats.call_args_list
        )

    def assert_all_called(self) -> None:
        assert all(
            (pattern.called for pattern in self.patterns)
        ), "RESPX: some mocked requests were not called!"

    def match(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: Union[SyncByteStream, AsyncByteStream] = None,
    ) -> Tuple[Optional[RequestPattern], Request, Optional[ResponseTemplate]]:
        request: Request = (method, url, headers, stream)

        matched_pattern: Optional[RequestPattern] = None
        matched_pattern_index: Optional[int] = None
        response: Optional[ResponseTemplate] = None

        for i, pattern in enumerate(self.patterns):
            match = pattern.match(request)
            if not match:
                continue

            if matched_pattern_index is not None:
                # Multiple matches found, drop and use the first one
                self.patterns.pop(matched_pattern_index)
                break

            matched_pattern = pattern
            matched_pattern_index = i

            if isinstance(match, ResponseTemplate):
                # Mock response
                response = match
            elif match == request:
                # Pass-through request
                response = None
            else:
                raise ValueError(
                    (
                        "Matched request pattern must return either a "
                        'ResponseTemplate or a Request, got "{}"'
                    ).format(type(match))
                )

        if matched_pattern is None:
            # Assert we always get a pattern match, if check is enabled
            assert not self._assert_all_mocked, f"RESPX: {request[1]!r} not mocked!"

            # Auto mock a successfull empty response
            response = ResponseTemplate()

        return matched_pattern, request, response

    def _sync_request(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: SyncByteStream = None,
        timeout: TimeoutDict = None,
        pass_through: Callable[..., Response] = None,
    ) -> Response:
        pattern, request, response_template = self.match(method, url, headers, stream)

        try:
            if response_template is None:
                # Pass-through request
                if pass_through is None:
                    raise ValueError("pass_through not supported with manual transport")
                response = pass_through(method, url, headers, stream, timeout)
            else:
                response = response_template.raw
            return response
        except Exception:
            response = None
            raise
        finally:
            self.record(request, response, pattern=pattern)

    async def _async_request(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: AsyncByteStream = None,
        timeout: TimeoutDict = None,
        pass_through: Callable[..., Coroutine[Any, Any, Response]] = None,
    ) -> Response:
        pattern, request, response_template = self.match(method, url, headers, stream)

        try:
            if response_template is None:
                # Pass-through request
                if pass_through is None:
                    raise ValueError("pass_through not supported with manual transport")
                response = await pass_through(method, url, headers, stream, timeout)
            else:
                response = await response_template.araw
            return response
        except Exception:
            response = None
            raise
        finally:
            self.record(request, response, pattern=pattern)

    def close(self) -> None:
        if self._assert_all_called:
            self.assert_all_called()

    async def aclose(self) -> None:
        self.close()


class SyncMockTransport(BaseMockTransport, SyncHTTPTransport):
    def request(  # type: ignore
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: SyncByteStream = None,
        timeout: TimeoutDict = None,
    ) -> Response:
        return self._sync_request(method, url, headers, stream, timeout)


class AsyncMockTransport(BaseMockTransport, AsyncHTTPTransport):
    async def request(  # type: ignore
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: AsyncByteStream = None,
        timeout: TimeoutDict = None,
    ) -> Response:
        return await self._async_request(method, url, headers, stream, timeout)
