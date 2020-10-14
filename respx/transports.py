from typing import Callable, Dict, List, Optional, Tuple, Union, overload
from warnings import warn

from httpcore import (
    AsyncByteStream,
    AsyncHTTPTransport,
    SyncByteStream,
    SyncHTTPTransport,
)

from .models import (
    URL,
    AsyncResponse,
    CallList,
    ContentDataTypes,
    DefaultType,
    Headers,
    HeaderTypes,
    JSONTypes,
    QueryParamTypes,
    Request,
    RequestPattern,
    Response,
    ResponseTemplate,
    SyncResponse,
    URLPatternTypes,
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

        self.calls = CallList()

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

        for pattern in self.patterns:
            pattern.calls.clear()

    @property
    def stats(self):
        warn(
            ".stats property is deprecated. Please, use .calls",
            category=DeprecationWarning,
        )
        return self.calls

    def __getitem__(self, alias: str) -> Optional[RequestPattern]:
        return self.aliases.get(alias)

    @overload
    def pop(self, alias: str) -> RequestPattern:
        ...  # pragma: nocover

    @overload
    def pop(
        self, alias: str, default: DefaultType
    ) -> Union[RequestPattern, DefaultType]:
        ...  # pragma: nocover

    def pop(self, alias, default=...):
        """
        Removes a pattern by alias and returns it.

        Raises KeyError when `default` not provided and alias is not found.
        """
        try:
            request_pattern = self.aliases.pop(alias)
            self.patterns.remove(request_pattern)
            return request_pattern
        except KeyError as ex:
            if default is ...:
                raise ex
            return default

    def add(
        self,
        method: Union[str, Callable, RequestPattern],
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
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
                status_code,
                headers=headers,
                content_type=content_type,
                content=content,
                text=text,
                html=html,
                json=json,
            )
            pattern = RequestPattern(
                method,
                url,
                params=params,
                response=response,
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
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "GET",
            url=url,
            params=params,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            pass_through=pass_through,
            alias=alias,
        )

    def post(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "POST",
            url=url,
            params=params,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            pass_through=pass_through,
            alias=alias,
        )

    def put(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "PUT",
            url=url,
            params=params,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            pass_through=pass_through,
            alias=alias,
        )

    def patch(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "PATCH",
            url=url,
            params=params,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            pass_through=pass_through,
            alias=alias,
        )

    def delete(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "DELETE",
            url=url,
            params=params,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            pass_through=pass_through,
            alias=alias,
        )

    def head(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "HEAD",
            url=url,
            params=params,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            pass_through=pass_through,
            alias=alias,
        )

    def options(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
    ) -> RequestPattern:
        return self.add(
            "OPTIONS",
            url=url,
            params=params,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            content=content,
            text=text,
            html=html,
            json=json,
            pass_through=pass_through,
            alias=alias,
        )

    def record(
        self,
        request: Request,
        response: Optional[Response],
        pattern: Optional[RequestPattern] = None,
    ) -> None:
        # TODO: Skip recording stats for pass_through requests?
        call = self.calls.record(request, response)
        if pattern:
            pattern.calls.append(call)

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

            # Auto mock a successful empty response
            response = ResponseTemplate()

        return matched_pattern, request, response

    def request(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: SyncByteStream = None,
        ext: dict = None,
    ) -> SyncResponse:
        pattern, request, response_template = self.match(method, url, headers, stream)

        try:
            if response_template is None:
                # Pass-through request
                pass_through = ext.pop("pass_through", None)
                if pass_through is None:
                    raise ValueError("pass_through not supported with manual transport")
                response = pass_through(method, url, headers, stream, ext)
            else:
                response = response_template.raw
            return response
        except Exception:
            response = None
            raise
        finally:
            self.record(
                request, response, pattern=pattern
            )  # pragma: nocover  # python 3.9 bug

    async def arequest(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: AsyncByteStream = None,
        ext: dict = None,
    ) -> AsyncResponse:
        pattern, request, response_template = self.match(method, url, headers, stream)

        try:
            if response_template is None:
                # Pass-through request
                pass_through = ext.pop("pass_through", None)
                if pass_through is None:
                    raise ValueError("pass_through not supported with manual transport")
                response = await pass_through(method, url, headers, stream, ext)
            else:
                response = await response_template.araw
            return response
        except Exception:
            response = None
            raise
        finally:
            self.record(
                request, response, pattern=pattern
            )  # pragma: nocover  # python 3.9 bug

    def close(self) -> None:
        if self._assert_all_called:
            self.assert_all_called()

    async def aclose(self) -> None:
        self.close()


class SyncMockTransport(BaseMockTransport, SyncHTTPTransport):
    ...


class AsyncMockTransport(BaseMockTransport, AsyncHTTPTransport):
    ...
