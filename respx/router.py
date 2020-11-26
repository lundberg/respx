import inspect
from functools import wraps
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, overload
from warnings import warn

import httpx

from .mocks import BaseMock, HTTPCoreMock, HTTPCoreMock as DefaultMock
from .models import CallList, Route, SideEffectError
from .patterns import Pattern, merge_patterns, parse_url_patterns
from .types import DefaultType, URLPatternTypes

Default = object
DEFAULT = Default()


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

        self._snapshots: List[Tuple] = []
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
        routes = dict(self.routes)
        calls = CallList(self.calls)
        self._snapshots.append((routes, calls))

        # Snapshot each route state
        for route in routes.values():
            route.snapshot()

    def rollback(self) -> None:
        """
        Rollbacks routes, and optionally calls, to snapshot state.
        """
        if not self._snapshots:
            return

        # Revert added routes and calls to last snapshot
        routes, calls = self._snapshots.pop()
        self.routes.clear()
        self.routes.update(routes)
        self.calls[:] = calls

        # Revert each route state to last snapshot
        for route in self.routes.values():
            route.rollback()

    def reset(self) -> None:
        """
        Resets call stats.
        """
        self.calls.clear()
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

        if route.id in self.routes:
            route = self.replace(route)
        else:
            self.routes[route.id] = route

        return route

    def replace(self, route: Route) -> Route:
        """
        Replace existing route with same pattern, in same place (order).
        """
        existing_route = self.routes[route.id]
        existing_route.return_value = route.return_value
        existing_route.side_effect = route.side_effect
        existing_route.pass_through(route.is_pass_through)
        return existing_route

    def request(
        self,
        method: str,
        url: Optional[URLPatternTypes] = None,
        *,
        name: Optional[str] = None,
        **lookups: Any,
    ) -> Route:
        return self.route(method=method, url=url, name=name, **lookups)

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

    def resolve(self, request: httpx.Request) -> Optional[httpx.Response]:
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


class MockRouter(Router):
    Mock: Optional[Type[BaseMock]]
    handler = Router.resolve
    _local = False

    def __init__(
        self,
        *,
        assert_all_called: bool = True,
        assert_all_mocked: bool = True,
        base_url: Optional[str] = None,
        using: Optional[Union[str, Default]] = DEFAULT,
    ) -> None:
        super().__init__(
            assert_all_called=assert_all_called,
            assert_all_mocked=assert_all_mocked,
            base_url=base_url,
        )
        self.Mock = {
            "httpcore": HTTPCoreMock,
            DEFAULT: DefaultMock,
        }.get(using)

    def __call__(
        self,
        func: Optional[Callable] = None,
        *,
        assert_all_called: Optional[bool] = None,
        assert_all_mocked: Optional[bool] = None,
        base_url: Optional[str] = None,
        using: Optional[Union[str, Default]] = DEFAULT,
    ) -> Union["MockRouter", Callable]:
        """
        Decorator or Context Manager.

        Use decorator/manager with parentheses for local state, or without parentheses
        for global state, i.e. shared patterns added outside of scope.
        """
        if func is None:
            # Parantheses used, branch out to new nested instance.
            # - Only stage when using local ctx `with respx.mock(...) as respx_mock:`
            # - First stage when using local decorator `@respx.mock(...)`
            #   FYI, global ctx `with respx.mock:` hits __enter__ directly
            settings: Dict[str, Any] = {
                "base_url": base_url,
                "using": using,
            }
            if assert_all_called is not None:
                settings["assert_all_called"] = assert_all_called
            if assert_all_mocked is not None:
                settings["assert_all_mocked"] = assert_all_mocked
            respx_mock = self.__class__(**settings)
            respx_mock._local = True
            return respx_mock

        # Async Decorator
        @wraps(func)
        async def async_decorator(*args, **kwargs):
            assert func is not None
            if self._local:
                kwargs["respx_mock"] = self
            async with self:
                return await func(*args, **kwargs)

        # Sync Decorator
        @wraps(func)
        def sync_decorator(*args, **kwargs):
            assert func is not None
            if self._local:
                kwargs["respx_mock"] = self
            with self:
                return func(*args, **kwargs)

        # Dispatch async/sync decorator, depening on decorated function.
        # - Only stage when using global decorator `@respx.mock`
        # - Second stage when using local decorator `@respx.mock(...)`
        return async_decorator if inspect.iscoroutinefunction(func) else sync_decorator

    def __enter__(self) -> "MockRouter":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.stop(quiet=bool(exc_type is not None))

    async def __aenter__(self) -> "MockRouter":
        return self.__enter__()

    async def __aexit__(self, *args: Any) -> None:
        self.__exit__(*args)

    def start(self) -> None:
        """
        Register transport, snapshot router and start patching.
        """
        self.snapshot()
        if self.Mock:
            self.Mock.register(self)
            self.Mock.start()

    def stop(self, clear: bool = True, reset: bool = True, quiet: bool = False) -> None:
        """
        Unregister transport and rollback router.
        Stop patching when no registered transports left.
        """
        unregistered = self.Mock.unregister(self) if self.Mock else True

        try:
            if unregistered and not quiet and self._assert_all_called:
                self.assert_all_called()
        finally:
            if clear:
                self.rollback()
            if reset:
                self.reset()
            if self.Mock:
                self.Mock.stop()


class DeprecatedMockTransport(MockRouter):
    def __init__(self, *args, **kwargs):
        warn(
            "MockTransport used as router is deprecated. Please use `respx.mock(...)`.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
