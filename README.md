# responsex

![](https://github.com/lundberg/responsex/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/lundberg/responsex/branch/master/graph/badge.svg)](https://codecov.io/gh/lundberg/responsex)
[![PyPi Version](https://img.shields.io/pypi/v/responsex.svg)](https://pypi.org/project/responsex/)
[![Python Versions](https://img.shields.io/pypi/pyversions/responsex.svg)](https://pypi.org/project/responsex/)

A utility for mocking out the Python [httpx](https://github.com/encode/httpx) library.

```py
import httpx
import responsex

with responsex.HTTPXMock() as httpx_mock:
    httpx_mock.add("GET", "https://foo.bar/", content={"foo": "bar"})
    response = httpx.get("https://foo.bar")
    assert response.json() == {"foo": "bar"}
```
