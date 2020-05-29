from typing import Callable, Optional, Pattern, Union

from .mocks import MockTransport
from .models import ContentDataTypes, HeaderTypes, RequestPattern

mock = MockTransport(assert_all_called=False)

aliases = mock.aliases
stats = mock.stats
calls = mock.calls


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


def add(
    method: Union[str, Callable],
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.add(
        method,
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def request(
    method: Union[str, Callable],
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.request(
        method,
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def get(
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.get(
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def post(
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.post(
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def put(
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.put(
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def patch(
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.patch(
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def delete(
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.delete(
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def head(
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.head(
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )


def options(
    url: Optional[Union[str, Pattern]] = None,
    status_code: Optional[int] = None,
    content: Optional[ContentDataTypes] = None,
    content_type: Optional[str] = None,
    headers: Optional[HeaderTypes] = None,
    pass_through: bool = False,
    alias: Optional[str] = None,
) -> RequestPattern:
    global mock
    return mock.options(
        url=url,
        status_code=status_code,
        content=content,
        content_type=content_type,
        headers=headers,
        pass_through=pass_through,
        alias=alias,
    )
