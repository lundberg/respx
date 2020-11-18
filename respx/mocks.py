import inspect
from functools import wraps
from types import TracebackType
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union
from unittest import mock
from warnings import warn

from .models import decode_request, encode_response
from .router import Router

__all__ = ["MockRouter"]


class MockRouter(Router):
    _local = False
    Mock: Type["BaseMock"]

    def init(self):
        super().init()
        self.Mock = HTTPCoreMock

    def __call__(
        self,
        func: Optional[Callable] = None,
        *,
        assert_all_called: Optional[bool] = None,
        assert_all_mocked: Optional[bool] = None,
        base_url: Optional[str] = None,
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
        self.Mock.register(self)
        self.Mock.start()

    def stop(self, clear: bool = True, reset: bool = True, quiet: bool = False) -> None:
        """
        Unregister transport and rollback router.
        Stop patching when no registered transports left.
        """
        unregistered = self.Mock.unregister(self)

        try:
            if unregistered and not quiet and self._assert_all_called:
                self.assert_all_called()
        finally:
            if clear:
                self.rollback()
            if reset:
                self.reset()

            self.Mock.stop()


class BaseMock:
    _patches: ClassVar[List[mock._patch]]
    routers: ClassVar[List[Router]]
    targets: ClassVar[List[str]]
    _target_methods: ClassVar[List[str]]

    @classmethod
    def register(cls, router: Router) -> None:
        cls.routers.append(router)

    @classmethod
    def unregister(cls, router: Router) -> bool:
        if router in cls.routers:
            cls.routers.remove(router)
            return True
        return False

    @classmethod
    def start(cls) -> None:
        # Ensure we only patch once!
        if cls._patches:
            return

        # Start patching target transports
        for target in cls.targets:
            for method in cls._target_methods:
                try:
                    spec = f"{target}.{method}"
                    patch = mock.patch(spec, spec=True, new_callable=cls._mock)
                    patch.start()
                    cls._patches.append(patch)
                except AttributeError:
                    pass

    @classmethod
    def stop(cls) -> None:
        # Ensure we don't stop patching when registered transports exists
        if cls.routers:
            return

        # Stop patching HTTPX
        while cls._patches:
            patch = cls._patches.pop()
            patch.stop()

    @classmethod
    def _merge_args_and_kwargs(cls, argspec, args, kwargs):
        arg_names = argspec.args[1:]  # Skip self
        new_kwargs = dict(zip(arg_names[-len(argspec.defaults) :], argspec.defaults))
        new_kwargs.update(zip(arg_names, args))
        new_kwargs.update(kwargs)
        return new_kwargs

    @classmethod
    def _mock(cls, spec):
        argspec = inspect.getfullargspec(spec)

        def mock(self, *args, **kwargs):
            kwargs = cls._merge_args_and_kwargs(argspec, args, kwargs)
            request = cls.to_httpx_request(**kwargs)
            request, kwargs = cls.prepare(request, **kwargs)
            response = cls.send(request, target=self, pass_through=spec, **kwargs)
            return response

        async def amock(self, *args, **kwargs):
            kwargs = cls._merge_args_and_kwargs(argspec, args, kwargs)
            request = cls.to_httpx_request(**kwargs)
            request, kwargs = await cls.aprepare(request, **kwargs)
            response = cls.send(request, target=self, pass_through=spec, **kwargs)
            if inspect.isawaitable(response):
                response = await response
            return response

        return amock if inspect.iscoroutinefunction(spec) else mock

    @classmethod
    def send(cls, httpx_request, *, target, pass_through, **kwargs):
        response = None
        error = None
        for router in cls.routers:
            try:
                httpx_response = router.resolve(httpx_request)
                if httpx_response is None:
                    response = pass_through(target, **kwargs)
                else:
                    response = cls.from_httpx_response(httpx_response, target, **kwargs)
            except AssertionError as e:
                error = e.args[0]
                continue
            else:
                break
        else:
            assert response, error
        return response

    @classmethod
    def prepare(cls, httpx_request, **kwargs):
        raise NotImplementedError()  # pragma: nocover

    @classmethod
    async def aprepare(cls, httpx_request, **kwargs):
        raise NotImplementedError()  # pragma: nocover

    @classmethod
    def to_httpx_request(cls, **kwargs):
        raise NotImplementedError()  # pragma: nocover

    @classmethod
    def from_httpx_response(cls, httpx_response, target, **kwargs):
        raise NotImplementedError()  # pragma: nocover


class HTTPCoreMock(BaseMock):
    _patches: ClassVar[List[mock._patch]] = []
    routers: ClassVar[List[Router]] = []
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
    _target_methods = ["request", "arequest"]

    @classmethod
    def prepare(cls, httpx_request, **kwargs):
        httpx_request.read()
        kwargs["stream"] = httpx_request.stream
        return httpx_request, kwargs

    @classmethod
    async def aprepare(cls, httpx_request, **kwargs):
        await httpx_request.aread()
        kwargs["stream"] = httpx_request.stream
        return httpx_request, kwargs

    @classmethod
    def to_httpx_request(cls, **kwargs):
        request = (kwargs["method"], kwargs["url"], kwargs["headers"], kwargs["stream"])
        httpx_request = decode_request(request)
        return httpx_request

    @classmethod
    def from_httpx_response(cls, httpx_response, target, **kwargs):
        return encode_response(httpx_response)


class DeprecatedMockTransport(MockRouter):
    def __init__(self, *args, **kwargs):
        warn(
            "MockTransport used as router is deprecated. Please use `respx.mock(...)`.",
            category=DeprecationWarning,
        )
        super().__init__(*args, **kwargs)
