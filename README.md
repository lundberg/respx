<p align="center">
  <a href="https://lundberg.github.io/respx/"><img width="350" height="208" src="https://raw.githubusercontent.com/lundberg/respx/master/docs/img/respx.png" alt='RESPX'></a>
</p>
<p align="center">
  <strong>RESPX</strong> <em>- Mock HTTPX with awesome request patterns and response side effects.</em>
</p>

---

![](https://github.com/lundberg/respx/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/lundberg/respx/branch/master/graph/badge.svg)](https://codecov.io/gh/lundberg/respx)
[![PyPi Version](https://img.shields.io/pypi/v/respx.svg)](https://pypi.org/project/respx/)
[![Python Versions](https://img.shields.io/pypi/pyversions/respx.svg)](https://pypi.org/project/respx/)

## Documentation

Full documentation is available at [lundberg.github.io/respx](https://lundberg.github.io/respx/)

## QuickStart

RESPX is a simple, *yet powerful*, utility for mocking out the [HTTPX](https://www.python-httpx.org/), *and [HTTP Core](https://www.encode.io/httpcore/)*, libraries.

Start by [patching](https://lundberg.github.io/respx/guide/#mock-httpx) `HTTPX`, using `respx.mock`, then add request [routes](https://lundberg.github.io/respx/guide/#routing-requests) to mock [responses](https://lundberg.github.io/respx/guide/#mocking-responses).

``` python
import httpx
import respx

from httpx import Response


@respx.mock
def test_example():
    my_route = respx.get("https://example.org/").mock(return_value=Response(204))
    response = httpx.get("https://example.org/")
    assert my_route.called
    assert response.status_code == 204
```

> Read the [User Guide](https://lundberg.github.io/respx/guide/) for a complete walk-through.


## Installation

Install with pip:

``` console
$ pip install respx
```

Requires Python 3.6+ and HTTPX 0.18+.
See [Changelog](https://github.com/lundberg/respx/blob/master/CHANGELOG.md) for older HTTPX compatibility.
