from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Pattern as Regex,
    Tuple,
    Union,
    overload,
)
from warnings import warn

import httpx

from .models import CallList, MockResponse, Route, SideEffectError
from .patterns import Pattern, merge_patterns, parse_url_patterns
from .types import (
    ContentDataTypes,
    DefaultType,
    HeaderTypes,
    JSONTypes,
    QueryParamTypes,
    URLPatternTypes,
)


class Router:
    def __init__(
        self,
        *,
        assert_all_called: bool = True,
        assert_all_mocked: bool = True,
        base_url: Optional[str] = None,
    ) -> None:
        self._assert_all_called = assert_all_called
        self._assert_all_mocked = assert_all_mocked
        self._bases = parse_url_patterns(base_url, exact=False)

        self.routes: Dict[Union[str, int], Route] = {}
        self.calls = CallList()
        self.snapshot()

    def clear(self) -> None:
        """
        Clears all routes. May be rolled back to snapshot state.
        """
        self.routes.clear()

    def snapshot(self) -> None:
        """
        Snapshots current routes and calls state.
        """
        # Snapshot current routes and calls
        self._routes = dict(self.routes)
        self._calls = CallList(self.calls)

        # Snapshot each route state
        for route in self._routes.values():
            route.snapshot()

    def rollback(self, reset: bool = True) -> None:
        """
        Rollbacks routes, and optionally calls, to snapshot state.
        """
        # Revert added routes to snapshot
        self.routes.clear()
        self.routes.update(self._routes)

        # Revert each route state to snapshot
        for route in self.routes.values():
            route.rollback(reset=False)

        # Reset call stats to snapshot
        if reset:
            self.reset()

    def reset(self) -> None:
        """
        Resets call stats to snapshot state.
        """
        self.calls[:] = self._calls
        for route in self.routes.values():
            route.reset()

    def assert_all_called(self) -> None:
        assert all(
            (route.called for route in self.routes.values())
        ), "RESPX: some mocked requests were not called!"

    @property
    def stats(self):
        warn(
            ".stats property is deprecated. Please, use .calls",
            category=DeprecationWarning,
        )
        return self.calls

    @property
    def aliases(self):
        warn(
            ".aliases property is deprecated. Please, use .routes",
            category=DeprecationWarning,
        )
        return self.routes

    def __getitem__(self, name: str) -> Optional[Route]:
        return self.routes.get(name)

    @overload
    def pop(self, name: str) -> Route:
        ...  # pragma: nocover

    @overload
    def pop(self, name: str, default: DefaultType) -> Union[Route, DefaultType]:
        ...  # pragma: nocover

    def pop(self, name, default=...):
        """
        Removes a route by name and returns it.

        Raises KeyError when `default` not provided and name is not found.
        """
        try:
            return self.routes.pop(name)
        except KeyError as ex:
            if default is ...:
                raise ex
            return default

    def route(
        self, *patterns: Pattern, name: Optional[str] = None, **lookups: Any
    ) -> Route:
        route = Route(*patterns, **lookups)
        self.add(route, name=name)
        return route

    def add(
        self,
        route: Optional[Union[str, Route, Callable]] = None,
        url: Optional[URLPatternTypes] = None,
        *,
        params: Optional[QueryParamTypes] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        headers: Optional[HeaderTypes] = None,
        content_type: Optional[str] = None,
        content: Optional[ContentDataTypes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        json: Optional[JSONTypes] = None,
        pass_through: bool = False,
        alias: Optional[str] = None,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        """
        Adds a route with given mocked response details.
        """
        if callable(route) and not isinstance(route, Route):
            route = Route(**lookups).mock(side_effect=route)

        elif isinstance(route, str):
            warn(
                "Passing method as string to respx.add is deprecated. "
                "Please, use respx.route(method=...) or respx.get(...)",
                category=DeprecationWarning,
            )
            method = route
            route = None

        if route is None:
            url__lookup = "url__regex" if isinstance(url, Regex) else "url"
            lookups.update({"method": method, url__lookup: url, "params": params})
            route = Route(**lookups)

        response = None
        if (
            status_code is not None
            or headers is not None
            or content_type is not None
            or content is not None
            or text is not None
            or html is not None
            or json is not None
            or pass_through is True
        ):
            if route.side_effect:
                raise NotImplementedError(
                    "Mixing callback with response details is no longer supported"
                )

            warn(
                "Response kwargs among request pattern kwargs is deprecated. "
                "Please, use .respond(...) or % operator.",
                category=DeprecationWarning,
            )

            response = MockResponse(
                status_code,
                headers=headers,
                content_type=content_type,
                content=content,
                text=text,
                html=html,
                json=json,
            )

        if response:
            route.return_value = response

        if pass_through:
            route.pass_through()

        if alias:
            warn(
                'Route alias kwarg is deprecated. Please use name="".',
                category=DeprecationWarning,
            )
            name = alias
        if name:
            route.name = name

        # Merge bases
        route.pattern = merge_patterns(route.pattern, **self._bases)

        route_key = route.name or hash(route)
        if route_key in self.routes:
            # Identical route already exists, swap with new one
            existing_route = self.routes[route_key]
            existing_route.return_value = route.return_value
            existing_route.side_effect = route.side_effect
            existing_route._pass_through = route._pass_through
            route = existing_route
        else:
            self.routes[route_key] = route

        return route

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
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.add(
            method="GET",
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
            name=name,
            **lookups,
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
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.add(
            method="POST",
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
            name=name,
            **lookups,
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
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.add(
            method="PUT",
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
            name=name,
            **lookups,
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
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.add(
            method="PATCH",
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
            name=name,
            **lookups,
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
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.add(
            method="DELETE",
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
            name=name,
            **lookups,
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
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.add(
            method="HEAD",
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
            name=name,
            **lookups,
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
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.add(
            method="OPTIONS",
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
            name=name,
            **lookups,
        )

    def record(
        self,
        request: httpx.Request,
        *,
        response: Optional[httpx.Response] = None,
        route: Optional[Route] = None,
    ) -> None:
        call = self.calls.record(request, response)
        if route:
            route.calls.append(call)

    def match(
        self,
        request: httpx.Request,
    ) -> Tuple[Optional[Route], Optional[Union[httpx.Request, httpx.Response]]]:
        route: Optional[Route] = None
        response: Optional[Union[httpx.Request, httpx.Response]] = None

        for prospect in self.routes.values():
            response = prospect.match(request)
            if response:
                route = prospect
                break

        return route, response

    def resolve(self, request: httpx.Request) -> httpx.Response:
        route: Optional[Route] = None
        response: Optional[httpx.Response] = None

        try:
            route, mock = self.match(request)

            if route is None:
                # Assert we always get a route match, if check is enabled
                assert not self._assert_all_mocked, f"RESPX: {request!r} not mocked!"

                # Auto mock a successful empty response
                response = httpx.Response(200)

            elif mock == request:
                # Pass-through request
                response = None

            else:
                # Mocked response
                assert isinstance(mock, httpx.Response)
                response = mock

        except SideEffectError as error:
            self.record(request, response=None, route=error.route)
            raise error.origin
        else:
            self.record(request, response=response, route=route)

        return response
