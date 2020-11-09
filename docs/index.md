# RESPX

Mock [HTTPX](https://www.python-httpx.org/) with awesome request patterns and response side effects.

![](https://github.com/lundberg/respx/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/lundberg/respx/branch/master/graph/badge.svg)](https://codecov.io/gh/lundberg/respx)
[![PyPi Version](https://img.shields.io/pypi/v/respx.svg)](https://pypi.org/project/respx/)
[![Python Versions](https://img.shields.io/pypi/pyversions/respx.svg)](https://pypi.org/project/respx/)

---

## QuickStart

RESPX is a simple, *yet powerful*, utility for mocking out the [HTTPX](https://www.python-httpx.org/), *and [HTTP Core](https://www.encode.io/httpcore/)*, libraries.

Start by [patching](guide.md#mock-httpx) `HTTPX`, using `respx.mock`, then add request [routes](guide.md#routing-requests) to mock [responses](guide.md#mocking-responses).

``` python
import httpx
import respx

from httpx import Response


@respx.mock
def test_example():
    my_route = respx.get("https://example.org/").mock(Response(204))
    response = httpx.get("https://example.org/")
    assert my_route.called
    assert response.status_code == 204
```

> Read the [User Guide](guide.md) for a complete walk-through.


## Installation

Install with pip:

``` console
$ pip install respx
```

Requires Python 3.6+ and HTTPX 0.15+.
See [Changelog](https://github.com/lundberg/respx/blob/master/CHANGELOG.md) for older HTTPX compatibility.
