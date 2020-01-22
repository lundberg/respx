import httpx
import pytest

import respx
from respx.fixtures import session_event_loop as event_loop


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
async def httpx_mock():
    async with respx.mock(base_url="https://httpx.mock") as httpx_mock:
        httpx_mock.get("/", status_code=404, alias="index")
        yield httpx_mock


@pytest.fixture(scope="session")
async def mocked_foo(event_loop):
    async with respx.mock(base_url="https://foo.api") as httpx_mock:
        httpx_mock.get("/", status_code=202, alias="index")
        httpx_mock.get("/bar/", alias="bar")
        yield httpx_mock


@pytest.fixture(scope="session")
async def mocked_ham(event_loop):
    async with respx.mock(base_url="https://ham.api") as httpx_mock:
        httpx_mock.get("/", status_code=200, alias="index")
        yield httpx_mock
