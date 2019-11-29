import asyncio

import pytest

import respx


@pytest.yield_fixture
async def httpx_mock():
    async with respx.HTTPXMock() as httpx_mock:
        yield httpx_mock


@pytest.fixture
def future():
    loop = asyncio.get_event_loop()
    return loop.run_until_complete
