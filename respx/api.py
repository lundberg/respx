from typing import Any, Callable, Optional, Union, overload

from .mocks import MockTransport
from .models import CallList, Route
from .patterns import Pattern
from .types import (
    ContentDataTypes,
    DefaultType,
    HeaderTypes,
    JSONTypes,
    QueryParamTypes,
    URLPatternTypes,
)

mock = MockTransport(assert_all_called=False)

aliases = mock.routes
routes = mock.routes
stats = mock.calls
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


def add(
    method: Union[str, Callable, Route],
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
    global mock
    return mock.add(
        method,
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


def get(
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
    global mock
    return mock.get(
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
    global mock
    return mock.post(
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
    global mock
    return mock.put(
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
    global mock
    return mock.patch(
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
    global mock
    return mock.delete(
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
    global mock
    return mock.head(
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
    global mock
    return mock.options(
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
