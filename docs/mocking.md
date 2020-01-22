# Mocking HTTPX

To mock out `HTTPX`, use the `respx.mock` decorator / context manager.

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


## Global Setup & Teardown

### pytest
``` python
# conftest.py
import pytest
import respx


@pytest.fixture
def mocked_api():
    with respx.mock(base_url="https://foo.bar") as httpx_mock:
        httpx_mock.get("/user/", content=[], alias="list_users")
        ...
        yield httpx_mock
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
        self.mocked_api.get("/user/", content=[], alias="list_users")
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
```
``` python
@pytest.mark.asyncio
async def test_something():
    async with respx.mock:
        async with httpx.AsyncClient() as client:
            request = respx.get("https://foo.bar/", content="foobar")
            response = await client.get("https://foo.bar/")
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
    async with respx.mock(base_url="https://foo.bar") as httpx_mock:
        ...
        yield httpx_mock
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

    async def test_something(self):
        async with respx.mock:
            async with httpx.AsyncClient() as client:
                request = respx.get("https://foo.bar/", content="foobar")
                response = await client.get("https://foo.bar/")
```

