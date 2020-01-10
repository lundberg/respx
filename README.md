# RESPX

![](https://github.com/lundberg/respx/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/lundberg/respx/branch/master/graph/badge.svg)](https://codecov.io/gh/lundberg/respx)
[![PyPi Version](https://img.shields.io/pypi/v/respx.svg)](https://pypi.org/project/respx/)
[![Python Versions](https://img.shields.io/pypi/pyversions/respx.svg)](https://pypi.org/project/respx/)

A utility for mocking out the Python [HTTPX](https://github.com/encode/httpx) library.

## Documentation

Full documentation is available at [lundberg.github.io/respx](https://lundberg.github.io/respx/)

### QuickStart

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
