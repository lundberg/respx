# responsex

A utility for mocking out the Python [httpx](https://github.com/encode/httpx) library.

```py
import httpx
import responsex

with responsex.HTTPXMock() as httpx_mock:
    httpx_mock.add("GET", "https://foo.bar/", content={"foo": "bar"})
    response = httpx.get("https://foo.bar")
    assert response.json() == {"foo": "bar"}
```
