import inspect
from typing import TYPE_CHECKING, ClassVar, List
from unittest import mock

from .models import decode_request, encode_response

if TYPE_CHECKING:
    from .router import Router  # pragma: nocover

__all__ = ["HTTPCoreMock"]


class BaseMock:
    _patches: ClassVar[List[mock._patch]]
    routers: ClassVar[List["Router"]]
    targets: ClassVar[List[str]]
    target_methods: ClassVar[List[str]]

    @classmethod
    def register(cls, router: "Router") -> None:
        cls.routers.append(router)

    @classmethod
    def unregister(cls, router: "Router") -> bool:
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
            for method in cls.target_methods:
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
        """
        Sync pre-read request body
        """
        httpx_request.read()
        return httpx_request, kwargs

    @classmethod
    async def aprepare(cls, httpx_request, **kwargs):
        """
        Async pre-read request body
        """
        await httpx_request.aread()
        return httpx_request, kwargs

    @classmethod
    def to_httpx_request(cls, **kwargs):
        raise NotImplementedError()  # pragma: nocover

    @classmethod
    def from_httpx_response(cls, httpx_response, target, **kwargs):
        raise NotImplementedError()  # pragma: nocover


class HTTPCoreMock(BaseMock):
    _patches: ClassVar[List[mock._patch]] = []
    routers: ClassVar[List["Router"]] = []
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
    target_methods = ["request", "arequest"]

    @classmethod
    def prepare(cls, httpx_request, **kwargs):
        """
        Sync pre-read request body, and update transport request args.
        """
        httpx_request, kwargs = super().prepare(httpx_request, **kwargs)
        kwargs["stream"] = httpx_request.stream
        return httpx_request, kwargs

    @classmethod
    async def aprepare(cls, httpx_request, **kwargs):
        """
        Async pre-read request body, and update transport request args.
        """
        httpx_request, kwargs = await super().aprepare(httpx_request, **kwargs)
        kwargs["stream"] = httpx_request.stream
        return httpx_request, kwargs

    @classmethod
    def to_httpx_request(cls, **kwargs):
        """
        Create a `HTTPX` request from transport request args.
        """
        request = (kwargs["method"], kwargs["url"], kwargs["headers"], kwargs["stream"])
        httpx_request = decode_request(request)
        return httpx_request

    @classmethod
    def from_httpx_response(cls, httpx_response, target, **kwargs):
        """
        Create a transport return tuple from `HTTPX` response.
        """
        return encode_response(httpx_response)
