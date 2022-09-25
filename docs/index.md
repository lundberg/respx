<p align="center" style="margin: 0 0 10px">
  <img width="350" height="208" src="img/respx.png" alt="RESPX">
</p>

<h1 align="center" style="font-size: 3rem; margin: -15px 0">
RESPX
</h1>

---

Mock [HTTPX](https://www.python-httpx.org/) with awesome request patterns and response side effects.

[![tests](https://img.shields.io/github/workflow/status/lundberg/respx/test?label=tests&logo=github&logoColor=white&style=flat-square)](https://github.com/lundberg/respx/actions/workflows/test.yml) [![codecov](https://img.shields.io/codecov/c/github/lundberg/respx?logo=codecov&logoColor=white&style=flat-square)](https://codecov.io/gh/lundberg/respx) [![PyPi Version](https://img.shields.io/pypi/v/respx?logo=pypi&logoColor=white&style=flat-square)](https://pypi.org/project/respx/) [![Python Versions](https://img.shields.io/pypi/pyversions/respx?logo=python&logoColor=white&style=flat-square)](https://pypi.org/project/respx/)


## QuickStart

RESPX is a simple, *yet powerful*, utility for mocking out the [HTTPX](https://www.python-httpx.org/), *and [HTTP Core](https://www.encode.io/httpcore/)*, libraries.

Start by [patching](guide.md#mock-httpx) `HTTPX`, using `respx.mock`, then add request [routes](guide.md#routing-requests) to mock [responses](guide.md#mocking-responses).

``` python
import httpx
import respx

from httpx import Response


@respx.mock
def test_example():
    my_route = respx.get("https://foo.bar/").mock(return_value=Response(204))
    response = httpx.get("https://foo.bar/")
    assert my_route.called
    assert response.status_code == 204
```

> Read the [User Guide](guide.md) for a complete walk-through.


### pytest + httpx

For a neater `pytest` experience, RESPX includes a `respx_mock` *fixture* for easy `HTTPX` mocking, along with an optional `respx` *marker* to fine-tune the mock [settings](api.md#configuration).

``` python
import httpx
import pytest


def test_default(respx_mock):
    respx_mock.get("https://foo.bar/").mock(return_value=httpx.Response(204))
    response = httpx.get("https://foo.bar/")
    assert response.status_code == 204


@pytest.mark.respx(base_url="https://foo.bar")
def test_with_marker(respx_mock):
    respx_mock.get("/baz/").mock(return_value=httpx.Response(204))
    response = httpx.get("https://foo.bar/baz/")
    assert response.status_code == 204
```


## Installation

Install with pip:

``` console
$ pip install respx
```

Requires Python 3.7+ and HTTPX 0.21+.
See [Changelog](https://github.com/lundberg/respx/blob/master/CHANGELOG.md) for older HTTPX compatibility.
