import httpx
import pytest

import respx
from respx.fixtures import session_event_loop as event_loop  # noqa: F401


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
async def my_mock():
    async with respx.mock(base_url="https://httpx.mock") as respx_mock:
        respx_mock.get("/", status_code=404, alias="index")
        yield respx_mock


@pytest.fixture(scope="session")
async def mocked_foo(event_loop):  # noqa: F811
    async with respx.mock(base_url="https://foo.api") as respx_mock:
        respx_mock.get("/", status_code=202, alias="index")
        respx_mock.get("/bar/", alias="bar")
        yield respx_mock


@pytest.fixture(scope="session")
async def mocked_ham(event_loop):  # noqa: F811
    async with respx.mock(base_url="https://ham.api") as respx_mock:
        respx_mock.get("/", status_code=200, alias="index")
        yield respx_mock
