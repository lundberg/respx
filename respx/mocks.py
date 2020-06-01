import inspect
import warnings
from functools import partial, wraps
from typing import Any, Callable, Dict, List, Optional, Union

import asynctest

from .transports import BaseMockTransport

__all__ = ["MockTransport", "HTTPXMock"]


class MockTransport(BaseMockTransport):
    _patches: List[asynctest.mock._patch] = []
    transports: List["MockTransport"] = []
    targets = [
        "httpcore._sync.connection.SyncHTTPConnection.request",
        "httpcore._sync.connection_pool.SyncConnectionPool.request",
        "httpcore._sync.http_proxy.SyncHTTPProxy.request",
        "httpcore._async.connection.AsyncHTTPConnection.request",
        "httpcore._async.connection_pool.AsyncConnectionPool.request",
        "httpcore._async.http_proxy.AsyncHTTPProxy.request",
        "httpx._transports.asgi.ASGITransport.request",
        "httpx._transports.wsgi.WSGITransport.request",
        "httpx._transports.urllib3.URLLib3Transport.request",
    ]

    def __init__(
        self,
        assert_all_called: bool = True,
        assert_all_mocked: bool = True,
        base_url: Optional[str] = None,
        local: bool = False,
    ) -> None:
        self._local = local
        super().__init__(
            assert_all_called=assert_all_called,
            assert_all_mocked=assert_all_mocked,
            base_url=base_url,
        )

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
                "local": True,
            }
            if assert_all_called is not None:
                settings["assert_all_called"] = assert_all_called
            if assert_all_mocked is not None:
                settings["assert_all_mocked"] = assert_all_mocked
            return self.__class__(**settings)

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

    def __exit__(self, *args: Any) -> None:
        self.stop()

    async def __aenter__(self) -> "MockTransport":
        return self.__enter__()

    async def __aexit__(self, *args: Any) -> None:
        self.__exit__(*args)

    def start(self) -> None:
        """
        Register transport and start patching.
        """
        self.transports.append(self)
        self._patch()

    def stop(self, clear: bool = True, reset: bool = True) -> None:
        """
        Unregister transport and stop patching, when no registered transports left.
        """
        try:
            if self._assert_all_called:
                self.assert_all_called()
        finally:
            if clear:
                self.clear()
            if reset:
                self.reset()

            # Unregister current transport
            assert self in self.transports, "RESPX transport already stopped!"
            self.transports.remove(self)
            self._unpatch()

    @classmethod
    def _patch(cls) -> None:
        # Ensure we only patch once!
        if cls._patches:
            return

        # Start patching target transports
        for target in cls.targets:
            patch = asynctest.mock.patch(
                target, spec=True, create=True, new_callable=cls._mock,
            )
            patch.start()
            cls._patches.append(patch)

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
    def _mock(cls, spec):
        if inspect.iscoroutinefunction(spec):

            async def request(self, *args, **kwargs):
                kwargs["pass_through"] = partial(spec, self)
                response = None
                error = None
                for transport in cls.transports:
                    try:
                        response = await transport._async_request(*args, **kwargs)
                    except AssertionError as e:
                        error = e.args[0]
                        continue
                    else:
                        break
                else:
                    assert response, error
                return response

        else:

            def request(self, *args, **kwargs):
                kwargs["pass_through"] = partial(spec, self)
                response = None
                error = None
                for transport in cls.transports:
                    try:
                        response = transport._sync_request(*args, **kwargs)
                    except AssertionError as e:
                        error = e.args[0]
                        continue
                    else:
                        break
                else:
                    assert response, error
                return response

        return request


class HTTPXMock(MockTransport):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "HTTPXMock() is due to be deprecated. Use MockTransport() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
