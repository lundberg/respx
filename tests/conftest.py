import asyncio
from contextlib import contextmanager

import pytest

import respx


@contextmanager
def does_not_raise():
    yield


@pytest.yield_fixture
async def httpx_mock():
    async with respx.HTTPXMock() as httpx_mock:
        yield httpx_mock


@pytest.fixture
def future():
    loop = asyncio.get_event_loop()
    return loop.run_until_complete
