# Mocking HTTPX

To mock out `HTTPX`, use the `respx.mock` decorator / context manager.


## Using the Decorator

``` python
import httpx
import respx


@respx.mock
async def test_something():
    request = respx.get("https://foo.bar/", content="foobar")
    response = await httpx.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```


## Using the Context Manager

``` python
import httpx
import respx


async with respx.mock:
    request = respx.get("https://foo.bar/", content="foobar")
    response = await httpx.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```

## Advanced Usage

Use `respx.mock` *without* parentheses for **global** scope, or *with* parentheses for **local** scope and configurable checks.
For more details on checks, see RESPX [Built-in Assertions](api.md#built-in-assertions).

!!! note "NOTE"
    You can also start and stop mocking `HTTPX` manually, by calling `respx.start()` and `respx.stop()`.


## Sync Support

`HTTPX` is, *since version `0.8`*, an **async** only HTTP client.
You can still use the `respx.mock` decorator on regular **sync** functions to mock out `HTTPX` and responses.
