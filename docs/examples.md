# Test Case Examples

## pytest

### Built-in Fixture

RESPX includes the `respx_mock` pytest httpx *fixture*.

``` python
import httpx


def test_fixture(respx_mock):
    respx_mock.get("https://foo.bar/").mock(return_value=httpx.Response(204))
    response = httpx.get("https://foo.bar/")
    assert response.status_code == 204
```

### Built-in Marker

To configure the `respx_mock` fixture, use the `respx` *marker*.

``` python
import httpx
import pytest


@pytest.mark.respx(base_url="https://foo.bar")
def test_configured_fixture(respx_mock):
    respx_mock.get("/baz/").mock(return_value=httpx.Response(204))
    response = httpx.get("https://foo.bar/baz/")
    assert response.status_code == 204
```

> See router [configuration](api.md#configuration) reference for more details.


### Custom Fixtures
``` python
# conftest.py
import pytest
import respx

from httpx import Response


@pytest.fixture
def mocked_api():
    with respx.mock(
        base_url="https://foo.bar", assert_all_called=False
    ) as respx_mock:
        users_route = respx_mock.get("/users/", name="list_users")
        users_route.return_value = Response(200, json=[])
        ...
        yield respx_mock
```

``` python
# test_api.py
import httpx


def test_list_users(mocked_api):
    response = httpx.get("https://foo.bar/users/")
    assert response.status_code == 200
    assert response.json() == []
    assert mocked_api["list_users"].called
```

**Session Scoped Fixtures**

If a session scoped RESPX fixture is used in an async context, you also need to broaden the `pytest-asyncio`
 [event_loop](https://github.com/pytest-dev/pytest-asyncio#event_loop) fixture.
 You can use the `session_event_loop` utility for this. 

``` python
# conftest.py
import pytest
import respx

from respx.fixtures import session_event_loop as event_loop  # noqa: F401


@pytest.fixture(scope="session")
async def mocked_api(event_loop):  # noqa: F811
    async with respx.mock(base_url="https://foo.bar") as respx_mock:
        ...
        yield respx_mock
```

### Async Test Cases
``` python
import httpx
import respx


@respx.mock
@pytest.mark.asyncio
async def test_async_decorator():
    async with httpx.AsyncClient() as client:
        route = respx.get("https://example.org/")
        response = await client.get("https://example.org/")
        assert route.called
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_ctx_manager():
    async with respx.mock:
        async with httpx.AsyncClient() as client:
            route = respx.get("https://example.org/")
            response = await client.get("https://example.org/")
            assert route.called
            assert response.status_code == 200
```


## unittest

### SetUp & TearDown

``` python
# testcases.py
import respx

from httpx import Response


class MockedAPIMixin:
    @classmethod
    def setUpClass(cls):
        cls.mocked_api = respx.mock(
            base_url="https://foo.bar", assert_all_called=False
        )
        users_route = cls.mocked_api.get("/users/", name="list_users")
        users_route.return_value = Response(200, json=[])
        ...

    def setUp(self):
        self.mocked_api.start()

    def tearDown(self):
        self.mocked_api.stop()
```
``` python
# test_api.py
import httpx
import unittest

from .testcases import MockedAPIMixin


class APITestCase(MockedAPIMixin, unittest.TestCase):
    def test_list_users(self):
        response = httpx.get("https://foo.bar/users/")
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json(), [])
        self.assertTrue(self.mocked_api["list_users"].called)
```

### Async Test Cases
``` python
import asynctest
import httpx
import respx


class MyTestCase(asynctest.TestCase):
    @respx.mock
    async def test_async_decorator(self):
        async with httpx.AsyncClient() as client:
            route = respx.get("https://example.org/")
            response = await client.get("https://example.org/")
            assert route.called
            assert response.status_code == 200

    async def test_async_ctx_manager(self):
        async with respx.mock:
            async with httpx.AsyncClient() as client:
                route = respx.get("https://example.org/")
                response = await client.get("https://example.org/")
                assert route.called
                assert response.status_code == 200
```
