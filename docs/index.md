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
    my_route = respx.get("https://foo.bar/").mock(return_value=Response(204))
    response = httpx.get("https://foo.bar/")
    assert my_route.called
    assert response.status_code == 204
```

> Read the [User Guide](guide.md) for a complete walk-through.


!!! attention "Warning"
    As of RESPX version `0.15.0`, the API has changed, but kept with **deprecation** warnings, later to be **broken** for backward compatibility in `0.16.0`. Read the [Upgrade Guide](upgrade.md) for an easier transision to latest release.

## Installation

Install with pip:

``` console
$ pip install respx
```

Requires Python 3.6+ and HTTPX 0.15+.
See [Changelog](https://github.com/lundberg/respx/blob/master/CHANGELOG.md) for older HTTPX compatibility.
