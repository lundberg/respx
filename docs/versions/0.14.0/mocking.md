!!! attention "Warning"
    This is the documentaion of the older version `0.14.0`. See [latest](../../../) for current release.

# Mock HTTPX - Version 0.14.0

To mock out `HTTPX` *and/or* `HTTP Core`, use the `respx.mock` decorator / context manager.

Optionally configure [built-in assertion](api.md#built-in-assertions) checks and [base URL](api.md#base-url)
with `respx.mock(...)`.


## Using the Decorator

``` python
import httpx
import respx


@respx.mock
def test_something():
    request = respx.get("https://foo.bar/", content="foobar")
    response = httpx.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```


## Using the Context Manager

``` python
import httpx
import respx


with respx.mock:
    request = respx.get("https://foo.bar/", content="foobar")
    response = httpx.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```

!!! note "NOTE"
    You can also start and stop mocking `HTTPX` manually, by calling `respx.start()` and `respx.stop()`.


## Using the mock Transports

The built-in transports are the base of all mocking and patching in RESPX.

*In fact*, `respx.mock` is an actual instance of `MockTransport`.

### MockTransport
``` python
import httpx
import respx


mock_transport = respx.MockTransport()
request = mock_transport.get("https://foo.bar/", content="foobar")

with mock_transport:
    response = httpx.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```

### SyncMockTransport

If you don't *need* to patch the original `HTTPX`/`HTTP Core` transports, then use the `SyncMockTransport` or [`AsyncMockTransport`](#asyncmocktransport) directly, by passing the `transport` *arg* when instantiating your `HTTPX` client, or alike.

``` python
import httpx
import respx


mock_transport = respx.SyncMockTransport()
request = mock_transport.get("https://foo.bar/", content="foobar")

with httpx.Client(transport=mock_transport) as client:
    response = client.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```

### AsyncMockTransport

``` python
import httpx
import respx


mock_transport = respx.AsyncMockTransport()
request = mock_transport.get("https://foo.bar/", content="foobar")

async with httpx.AsyncClient(transport=mock_transport) as client:
    response = await client.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```

!!! note "NOTE"
    The mock transports takes the same configuration arguments as the decorator / context manager.


## Global Setup & Teardown

### pytest
``` python
# conftest.py
import pytest
import respx


@pytest.fixture
def mocked_api():
    with respx.mock(base_url="https://foo.bar") as respx_mock:
        respx_mock.get("/users/", content=[], alias="list_users")
        ...
        yield respx_mock
```

``` python
# test_api.py
import httpx


def test_list_users(mocked_api):
    response = httpx.get("https://foo.bar/users/")
    request = mocked_api["list_users"]
    assert request.called
    assert response.json() == []
```

!!! tip
    Use a **session** scoped fixture `@pytest.fixture(scope="session")` when your fixture contains **multiple**
    endpoints that not necessary gets called by a single test case, or [disable](api.md#built-in-assertions)
    the built-in `assert_all_called` check.


### unittest

``` python
# testcases.py

class MockedAPIMixin:
    def setUp(self):
        self.mocked_api = respx.mock(base_url="https://foo.bar")
        self.mocked_api.get("/users/", content=[], alias="list_users")
        ...
        self.mocked_api.start()

    def tearDown(self):
        self.mocked_api.stop()
```
``` python
# test_api.py

import unittest
import httpx

from .testcases import MockedAPIMixin


class MyTestCase(MockedAPIMixin, unittest.TestCase):
    def test_list_users(self):
        response = httpx.get("https://foo.bar/users/")
        request = self.mocked_api["list_users"]
        assert request.called
        assert response.json() == []
```

!!! tip
    Use `setUpClass` and `tearDownClass` when you mock **multiple** endpoints that not 
    necessary gets called by a single test method, or [disable](api.md#built-in-assertions)
    the built-in `assert_all_called` check.


## Async Support

You can use `respx.mock` in both **sync** and **async** contexts to mock out `HTTPX` responses.

### pytest
``` python
@respx.mock
@pytest.mark.asyncio
async def test_something():
    async with httpx.AsyncClient() as client:
        request = respx.get("https://foo.bar/", content="foobar")
        response = await client.get("https://foo.bar/")
        assert request.called
        assert response.text == "foobar"
```
``` python
@pytest.mark.asyncio
async def test_something():
    async with respx.mock:
        async with httpx.AsyncClient() as client:
            request = respx.get("https://foo.bar/", content="foobar")
            response = await client.get("https://foo.bar/")
            assert request.called
            assert response.text == "foobar"
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

### unittest

``` python
import asynctest


class MyTestCase(asynctest.TestCase):
    @respx.mock
    async def test_something(self):
        async with httpx.AsyncClient() as client:
            request = respx.get("https://foo.bar/", content="foobar")
            response = await client.get("https://foo.bar/")
            assert request.called
            assert response.text == "foobar"

    async def test_something(self):
        async with respx.mock:
            async with httpx.AsyncClient() as client:
                request = respx.get("https://foo.bar/", content="foobar")
                response = await client.get("https://foo.bar/")
                assert request.called
                assert response.text == "foobar"
```

