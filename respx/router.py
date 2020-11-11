from typing import Any, Dict, Optional, Tuple, Union, overload

import httpx

from .models import CallList, Route, SideEffectError
from .patterns import Pattern, merge_patterns, parse_url_patterns
from .types import DefaultType, URLPatternTypes


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
        return self.add(route, name=name)

    def add(self, route: Route, *, name: Optional[str] = None) -> Route:
        """
        Adds a route with optionally given name,
        replacing any existing route with same pattern.
        """
        if not isinstance(route, Route):
            raise ValueError(
                f"Invalid route {route!r}, please use respx.route(...).mock(...)"
            )

        # Merge bases
        route.pattern = merge_patterns(route.pattern, **self._bases)
        route.name = name

        route_id = route.name or hash(route)
        if route_id in self.routes:
            # Identical route already exists, swap with new one
            existing_route = self.routes[route_id]
            existing_route.return_value = route.return_value
            existing_route.side_effect = route.side_effect
            existing_route._pass_through = route._pass_through
            route = existing_route
        else:
            self.routes[route_id] = route

        return route

    def get(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method="GET", url=url, name=name, **lookups)

    def post(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method="POST", url=url, name=name, **lookups)

    def put(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method="PUT", url=url, name=name, **lookups)

    def patch(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method="PATCH", url=url, name=name, **lookups)

    def delete(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method="DELETE", url=url, name=name, **lookups)

    def head(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method="HEAD", url=url, name=name, **lookups)

    def options(
        self,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method="OPTIONS", url=url, name=name, **lookups)

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
