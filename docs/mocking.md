# Mocking HTTPX

To mock out `HTTPX`, use the `respx.mock` decorator / context manager.


## Mock Decorator

``` python
import httpx
import respx


@respx.mock
def test_something():
    request = respx.get("https://foo.bar/", content="foobar")
    response = httpx.get("https://foo.bar/")
    assert request.called
    assert response.status_code == 200
    assert response.text == "foobar"
```

## Mock Context Manager

``` python
import httpx
import respx


with respx.mock:
    request = respx.options("https://foo.bar/baz/", content={"some": "thing"})
    response = httpx.options("https://foo.bar/baz/")
    assert request.called
    assert response.json() == {"some": "thing"}
```

## Advanced Usage

Use `respx.mock` *without* parentheses for **global** scope, or *with* parentheses for **local** scope and configurable checks.
For more details on checks, see RESPX [Built-in Assertions](api.md#built-in-assertions).

!!! note "NOTE"
    You can also start and stop mocking `HTTPX` manually, by calling `respx.start()` and `respx.stop()`.
