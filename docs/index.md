# RESPX

![](https://github.com/lundberg/respx/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/lundberg/respx/branch/master/graph/badge.svg)](https://codecov.io/gh/lundberg/respx)
[![PyPi Version](https://img.shields.io/pypi/v/respx.svg)](https://pypi.org/project/respx/)
[![Python Versions](https://img.shields.io/pypi/pyversions/respx.svg)](https://pypi.org/project/respx/)

A utility for mocking out the Python [HTTPX](https://www.encode.io/httpx/) library.

---

## QuickStart

Start by mocking out `HTTPX`, using `respx.mock`, and then add desired request patterns to mock your responses.

``` python
import httpx
import respx


@respx.mock
def test_something():
    request = respx.post("https://foo.bar/baz/", status_code=201)
    response = httpx.post("https://foo.bar/baz/")
    assert request.called
    assert response.status_code == 201
```

## Documentation

The [QuickStart](#quickstart) section covers the basics. Continue reading in detail on how [Mocking HTTPX](mocking.md) is done, or head over to the [Developer Interface](api.md) for a complete guide on how to mock your responses.

## Installation

Install with pip:

``` console
$ pip install respx
```

See `HTTPX` documentation on [Installation](https://www.encode.io/httpx/#installation) for requirements.
