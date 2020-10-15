from typing import Callable, Optional, Union, overload

from .mocks import MockTransport
from .models import (
    CallList,
    ContentDataTypes,
    DefaultType,
    HeaderTypes,
    JSONTypes,
    QueryParamTypes,
    RequestPattern,
    URLPatternTypes,
)

mock = MockTransport(assert_all_called=False)

aliases = mock.aliases
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
def pop(alias: str) -> RequestPattern:
    ...  # pragma: nocover


@overload
def pop(alias: str, default: DefaultType) -> Union[RequestPattern, DefaultType]:
    ...  # pragma: nocover


def pop(alias, default=...):
    global mock
    return mock.pop(alias=alias, default=default)


def add(
    method: Union[str, Callable],
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
) -> RequestPattern:
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
) -> RequestPattern:
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
) -> RequestPattern:
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
) -> RequestPattern:
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
) -> RequestPattern:
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
) -> RequestPattern:
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
) -> RequestPattern:
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
) -> RequestPattern:
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
    )
