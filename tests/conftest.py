import httpx
import pytest

import respx
from respx.fixtures import session_event_loop as event_loop  # noqa: F401

pytest_plugins = ["pytester"]


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
async def my_mock():
    async with respx.mock(
        base_url="https://httpx.mock", using="httpcore"
    ) as respx_mock:
        respx_mock.get("/", name="index").respond(404)
        yield respx_mock


@pytest.fixture(scope="session")
async def mocked_foo(event_loop):  # noqa: F811
    async with respx.mock(
        base_url="https://foo.api/api/", using="httpcore"
    ) as respx_mock:
        respx_mock.get("/", name="index").respond(202)
        respx_mock.get("/bar/", name="bar")
        yield respx_mock


@pytest.fixture(scope="session")
async def mocked_ham(event_loop):  # noqa: F811
    async with respx.mock(base_url="https://ham.api", using="httpcore") as respx_mock:
        respx_mock.get("/", name="index").respond(200)
        yield respx_mock
