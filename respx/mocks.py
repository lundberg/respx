import inspect
from functools import partial, wraps
from typing import Any, Callable, Dict, List, Optional, Union
from unittest import mock

from .transports import BaseMockTransport

__all__ = ["MockTransport"]


class MockTransport(BaseMockTransport):
    _local = False
    _patches: List[mock._patch] = []
    transports: List["MockTransport"] = []
    targets = [
        "httpcore._sync.connection.SyncHTTPConnection",
        "httpcore._sync.connection_pool.SyncConnectionPool",
        "httpcore._sync.http_proxy.SyncHTTPProxy",
        "httpcore._async.connection.AsyncHTTPConnection",
        "httpcore._async.connection_pool.AsyncConnectionPool",
        "httpcore._async.http_proxy.AsyncHTTPProxy",
        "httpx._transports.asgi.ASGITransport",
        "httpx._transports.wsgi.WSGITransport",
    ]

    def __call__(
        self,
        func: Optional[Callable] = None,
        assert_all_called: Optional[bool] = None,
        assert_all_mocked: Optional[bool] = None,
        base_url: Optional[str] = None,
    ) -> Union["MockTransport", Callable]:
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

    def __enter__(self) -> "MockTransport":
        self.start()
        return self

    def __exit__(self, exception_type: Optional[Exception], *args: Any) -> None:
        self.stop(quiet=bool(exception_type is not None))

    async def __aenter__(self) -> "MockTransport":
        return self.__enter__()

    async def __aexit__(self, *args: Any) -> None:
        self.__exit__(*args)

    def start(self) -> None:
        """
        Register transport and start patching.
        """
        # Idempotent check, i.e. already started
        if self not in self.transports:
            self.snapshot()
            self.transports.append(self)

        self._patch()

    def stop(self, clear: bool = True, reset: bool = True, quiet: bool = False) -> None:
        """
        Unregister transport and stop patching, when no registered transports left.
        """
        started = bool(self in self.transports)

        try:
            if started and not quiet and self._assert_all_called:
                self.assert_all_called()
        finally:
            # Idempotent check, i.e. already started
            if started:
                if clear:
                    self.rollback(reset=False)
                if reset:
                    self.reset()
                self.transports.remove(self)

            self._unpatch()

    @classmethod
    def _patch(cls) -> None:
        # Ensure we only patch once!
        if cls._patches:
            return

        # Start patching target transports
        for transport in cls.targets:
            for method, new in (("request", cls._request), ("arequest", cls._arequest)):
                try:
                    spec = f"{transport}.{method}"
                    patch = mock.patch(spec, spec=True, new_callable=new)
                    patch.start()
                    cls._patches.append(patch)
                except AttributeError:
                    pass

    @classmethod
    def _unpatch(cls) -> None:
        # Ensure we don't stop patching when registered transports exists
        if cls.transports:
            return

        # Stop patching HTTPX
        while cls._patches:
            patch = cls._patches.pop()
            patch.stop()

    @classmethod
    def _request(cls, spec):
        def request(self, *args, **kwargs):
            pass_through = partial(spec, self)
            kwargs["ext"] = {**kwargs.get("ext", {}), "pass_through": pass_through}
            response = None
            error = None
            for transport in cls.transports:
                try:
                    response = transport.request(*args, **kwargs)
                except AssertionError as e:
                    error = e.args[0]
                    continue
                else:
                    break
            else:
                assert response, error
            return response

        return request

    @classmethod
    def _arequest(cls, spec):
        async def request(self, *args, **kwargs):
            pass_through = partial(spec, self)
            kwargs["ext"] = {**kwargs.get("ext", {}), "pass_through": pass_through}
            response = None
            error = None
            for transport in cls.transports:
                try:
                    response = await transport.arequest(*args, **kwargs)
                except AssertionError as e:
                    error = e.args[0]
                    continue
                else:
                    break
            else:
                assert response, error
            return response

        return request
