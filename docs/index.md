# RESPX

![](https://github.com/lundberg/respx/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/lundberg/respx/branch/master/graph/badge.svg)](https://codecov.io/gh/lundberg/respx)
[![PyPi Version](https://img.shields.io/pypi/v/respx.svg)](https://pypi.org/project/respx/)
[![Python Versions](https://img.shields.io/pypi/pyversions/respx.svg)](https://pypi.org/project/respx/)

A utility for mocking out the Python [HTTPX](https://www.encode.io/httpx/) and [HTTP Core](https://www.encode.io/httpcore/) libraries.

---

## QuickStart

Start by mocking out `HTTPX` *and/or* `HTTP Core`, using `respx.mock`, and then add desired request patterns to mock your responses.

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

## Usage

The [QuickStart](#quickstart) section covers the basics. Continue reading in detail on how [Mocking HTTPX](mocking.md) is done, or head over to the [Developer Interface](api.md) for a complete guide on how to mock your responses.

!!! tip
    You can use `RESPX` not only to mock out `HTTPX`, but to actually mock responses for any library using `HTTP Core`.

## Installation

Install with pip:

``` console
$ pip install respx
```

Requires Python 3.6+ and HTTPX 0.13.0+.
See [Changelog](https://github.com/lundberg/respx/blob/master/CHANGELOG.md) for older HTTPX compatibility.
