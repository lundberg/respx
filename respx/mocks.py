import inspect
from abc import ABC
from types import MappingProxyType
from typing import TYPE_CHECKING, ClassVar, Dict, List, Type
from unittest import mock

from .models import PassThrough, decode_request, encode_response
from .transports import MockTransport, TryTransport

if TYPE_CHECKING:
    from .router import Router  # pragma: nocover

__all__ = ["Mocker", "HTTPCoreMocker"]


class Mocker(ABC):
    _patches: ClassVar[List[mock._patch]]
    name: ClassVar[str]
    routers: ClassVar[List["Router"]]
    targets: ClassVar[List[str]]
    target_methods: ClassVar[List[str]]

    # Automatically register all the subclasses in this dict
    __registry: ClassVar[Dict[str, Type["Mocker"]]] = {}
    registry = MappingProxyType(__registry)

    def __init_subclass__(cls) -> None:
        if not getattr(cls, "name", None) or ABC in cls.__bases__:
            return

        if cls.name in cls.__registry:
            raise TypeError(
                "Subclasses of Mocker must define a unique name. "
                f"{cls.name!r} is already defined as {cls.__registry[cls.name]!r}"
            )

        cls.routers = []
        cls._patches = []
        cls.__registry[cls.name] = cls

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
    def add_targets(cls, *targets: str) -> None:
        targets = tuple(filter(lambda t: t not in cls.targets, targets))
        if targets:
            cls.targets.extend(targets)
            cls.restart()

    @classmethod
    def remove_targets(cls, *targets: str) -> None:
        targets = tuple(filter(lambda t: t in cls.targets, targets))
        if targets:
            for target in targets:
                cls.targets.remove(target)
            cls.restart()

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
                    patch = mock.patch(spec, spec=True, new_callable=cls.mock)
                    patch.start()
                    cls._patches.append(patch)
                except AttributeError:
                    pass

    @classmethod
    def stop(cls, force: bool = False) -> None:
        # Ensure we don't stop patching when registered transports exists
        if cls.routers and not force:
            return

        # Stop patching HTTPX
        while cls._patches:
            patch = cls._patches.pop()
            patch.stop()

    @classmethod
    def restart(cls) -> None:
        # Only stop and start if started
        if cls._patches:  # pragma: nocover
            cls.stop(force=True)
            cls.start()

    @classmethod
    def handler(cls, httpx_request):
        httpx_response = None
        error = None
        for router in cls.routers:
            try:
                httpx_response = router.handler(httpx_request)
            except AssertionError as e:
                error = e.args[0]
                continue
            else:
                break
        else:
            assert httpx_response, error
        return httpx_response

    @classmethod
    def mock(cls, spec):
        raise NotImplementedError()  # pragma: nocover


class HTTPXMocker(Mocker):
    name = "httpx"
    targets = [
        "httpx._client.Client",
        "httpx._client.AsyncClient",
    ]
    target_methods = ["_transport_for_url"]

    @classmethod
    def mock(cls, spec):
        mock_transport = MockTransport(handler=cls.handler)

        def _transport_for_url(self, *args, **kwargs):
            pass_through_transport = spec(self, *args, **kwargs)
            transport = TryTransport([mock_transport, pass_through_transport])
            return transport

        return _transport_for_url


class AbstractRequestMocker(Mocker):
    @classmethod
    def mock(cls, spec):
        argspec = inspect.getfullargspec(spec)

        def mock(self, *args, **kwargs):
            kwargs = cls._merge_args_and_kwargs(argspec, args, kwargs)
            request = cls.to_httpx_request(**kwargs)
            request, kwargs = cls.prepare(request, **kwargs)
            response = cls._send(request, instance=self, target_spec=spec, **kwargs)
            return response

        async def amock(self, *args, **kwargs):
            kwargs = cls._merge_args_and_kwargs(argspec, args, kwargs)
            request = cls.to_httpx_request(**kwargs)
            request, kwargs = await cls.aprepare(request, **kwargs)
            response = cls._send(request, instance=self, target_spec=spec, **kwargs)
            if inspect.isawaitable(response):
                response = await response
            return response

        return amock if inspect.iscoroutinefunction(spec) else mock

    @classmethod
    def _merge_args_and_kwargs(cls, argspec, args, kwargs):
        arg_names = argspec.args[1:]  # Skip self
        new_kwargs = dict(zip(arg_names[-len(argspec.defaults) :], argspec.defaults))
        new_kwargs.update(zip(arg_names, args))
        new_kwargs.update(kwargs)
        return new_kwargs

    @classmethod
    def _send(cls, httpx_request, *, instance, target_spec, **kwargs):
        try:
            httpx_response = cls.handler(httpx_request)
        except PassThrough:
            response = target_spec(instance, **kwargs)
        else:
            response = cls.from_httpx_response(httpx_response, instance, **kwargs)
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


class HTTPCoreMocker(AbstractRequestMocker):
    name = "httpcore"
    targets = [
        "httpcore._sync.connection.SyncHTTPConnection",
        "httpcore._sync.connection_pool.SyncConnectionPool",
        "httpcore._sync.http_proxy.SyncHTTPProxy",
        "httpcore._async.connection.AsyncHTTPConnection",
        "httpcore._async.connection_pool.AsyncConnectionPool",
        "httpcore._async.http_proxy.AsyncHTTPProxy",
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


DEFAULT_MOCKER: str = HTTPCoreMocker.name
