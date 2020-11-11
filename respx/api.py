from typing import Any, Optional, Union, overload

from .mocks import MockTransport
from .models import CallList, Route
from .patterns import Pattern
from .types import DefaultType, URLPatternTypes

mock = MockTransport(assert_all_called=False)

routes = mock.routes
calls: CallList = mock.calls


def start() -> None:
    global mock
    mock.start()


def stop(clear: bool = True, reset: bool = True) -> None:
    global mock
    mock.stop(clear=clear, reset=reset)


def clear() -> None:
    global mock
    mock.clear()


def reset() -> None:
    global mock
    mock.reset()


@overload
def pop(name: str) -> Route:
    ...  # pragma: nocover


@overload
def pop(name: str, default: DefaultType) -> Union[Route, DefaultType]:
    ...  # pragma: nocover


def pop(name, default=...):
    global mock
    return mock.pop(name, default=default)


def route(*patterns: Pattern, name: Optional[str] = None, **lookups: Any) -> Route:
    global mock
    return mock.route(*patterns, name=name, **lookups)


def add(route: Route, *, name: Optional[str] = None) -> Route:
    global mock
    return mock.add(route, name=name)


def get(
    url: Optional[URLPatternTypes] = None, *, name: Optional[str] = None, **lookups: Any
) -> Route:
    global mock
    return mock.get(url, name=name, **lookups)


def post(
    url: Optional[URLPatternTypes] = None, *, name: Optional[str] = None, **lookups: Any
) -> Route:
    global mock
    return mock.post(url, name=name, **lookups)


def put(
    url: Optional[URLPatternTypes] = None, *, name: Optional[str] = None, **lookups: Any
) -> Route:
    global mock
    return mock.put(url, name=name, **lookups)


def patch(
    url: Optional[URLPatternTypes] = None, *, name: Optional[str] = None, **lookups: Any
) -> Route:
    global mock
    return mock.patch(url, name=name, **lookups)


def delete(
    url: Optional[URLPatternTypes] = None, *, name: Optional[str] = None, **lookups: Any
) -> Route:
    global mock
    return mock.delete(url, name=name, **lookups)


def head(
    url: Optional[URLPatternTypes] = None, *, name: Optional[str] = None, **lookups: Any
) -> Route:
    global mock
    return mock.head(url, name=name, **lookups)


def options(
    url: Optional[URLPatternTypes] = None, *, name: Optional[str] = None, **lookups: Any
) -> Route:
    global mock
    return mock.options(url, name=name, **lookups)
