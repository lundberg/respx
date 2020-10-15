# Developer Interface

## Mocking Responses

### HTTP Method API

For regular and simple use, use the HTTP method shorthands.
See [Request API](#request-api) for parameters.

> ::: respx.get

> <code>respx.<strong>options</strong>(...)</strong></code>

> <code>respx.<strong>head</strong>(...)</strong></code>

> <code>respx.<strong>post</strong>(...)</strong></code>

> <code>respx.<strong>put</strong>(...)</strong></code>

> <code>respx.<strong>patch</strong>(...)</strong></code>

> <code>respx.<strong>delete</strong>(...)</strong></code>


### Pattern API

For full control, use the core `add` method.

> ::: respx.add
>     :docstring:
>
> **Parameters:**
>
> * **method** - *str | callable | RequestPattern*  
>   Request HTTP method, or [Request callback](#request-callback), to match.
> * **url** - *(optional) str | pattern*  
>   Request exact URL, or [URL pattern](#url-pattern), to match.
> * **status_code** - *(optional) int - default: `200`*  
>   Response status code to mock.
> * **content** - *(optional) bytes | str | list | dict | callable | exception - default `b""`*  
>   Response content to mock. - *See [Response Content](#response-content).*
> * **content_type** - *(optional) str - default `text/plain`*  
>   Response Content-Type header value to mock.
> * **headers** - *(optional) dict*  
>   Response headers to mock.
> * **pass_through** - *(optional) bool - default `False`*  
>   Mark matched request to pass-through to real server, *e.g. don't mock*.
> * **alias** - *(optional) str*  
>   Name this request pattern. - *See [Call Statistics](#call-statistics).*

---

## Matching Requests

### Exact URL

To match and mock a request by an exact URL, pass the `url` parameter as a *string*.

``` python
respx.get("https://foo.bar/", status_code=204)
```


### URL pattern

Instead of matching an [exact URL](#exact-url), you can pass a *compiled regex* to match the request URL.

``` python
import httpx
import re
import respx


@respx.mock
def test_something():
    url_pattern = re.compile(r"^https://foo.bar/\w+/$")
    respx.get(url_pattern, content="Baz")
    response = httpx.get("https://foo.bar/baz/")
    assert response.text == "Baz"
```
!!! tip
    Named groups in the regex pattern will be passed as `kwargs` to the response content [callback](#content-callback), if used.


### Base URL

When adding a lot of request patterns sharing the same domain/prefix, you can configure RESPX with a `base_url` to use as the base when matching URLs.

Like `url`, the `base_url` can also be passed as a *compiled regex*, with optional named groups.

``` python
import httpx
import respx


@respx.mock(base_url="https://foo.bar")
async def test_something(respx_mock):
    async with httpx.AsyncClient(base_url="https://foo.bar") as client:
        request = respx_mock.get("/baz/", content="Baz")
        response = await client.get("/baz/")
        assert response.text == "Baz"
```


### Request callback

For full control of what request to **match** and what response to **mock**,
pass a *callback* function as the `add(method, ...)` parameter.
The callback's response argument will be pre-populated with any additional response parameters.

``` python
import httpx
import respx


def match_and_mock(request, response):
    """
    Return `None` to not match the request.
    Return the `response` to match and mock this request.
    Return the `request` for pass-through behaviour.
    """
    if request.method != "POST":
        return None

    if "X-Auth-Token" not in request.headers:
        response.status_code = 401
    else:
        response.content = "OK"

    return response


@respx.mock
def test_something():
    custom_request = respx.add(match_and_mock, status_code=201)
    respx.get("https://foo.bar/baz/")

    response = httpx.get("https://foo.bar/baz/")
    assert response.status_code == 200
    assert not custom_request.called

    response = httpx.post("https://foo.bar/baz/")
    assert response.status_code == 401
    assert custom_request.called

    response = httpx.post("https://foo.bar/baz/", headers={"X-Auth-Token": "x"})
    assert response.status_code == 201
    assert custom_request.call_count == 2
```


### Repeated patterns

If you mock several responses with the same *request pattern*, they will be matched in order, and popped til the last one.

``` python
import httpx
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/baz/123/", status_code=404)
    respx.get("https://foo.bar/baz/123/", content={"id": 123})
    respx.post("https://foo.bar/baz/", status_code=201)

    response = httpx.get("https://foo.bar/baz/123/")
    assert response.status_code == 404  # First match

    response = httpx.post("https://foo.bar/baz/")
    assert response.status_code == 201

    response = httpx.get("https://foo.bar/baz/123/")
    assert response.status_code == 200  # Second match
    assert response.json() == {"id": 123}
```

### Manipulating Existing Patterns

Clearing all existing patterns:

``` python
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/baz", status_code=404)
    respx.clear()  # no patterns will be matched after this call
```

Removing and optionally re-using an existing pattern by alias:

``` python
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/", status_code=404, alias="index")
    request_pattern = respx.pop("index")
    respx.get(request_pattern.url, status_code=200)
```

---

## Response Content

### JSON content

To mock a response with json content, pass a `list` or a `dict`.  
The `Content-Type` header will automatically be set to `application/json`.

``` python
import httpx
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/baz/123/", content={"id": 123})
    response = httpx.get("https://foo.bar/baz/123/")
    assert response.json() == {"id": 123}
```

### Content callback

If you need dynamic response content, pass a *callback* function.  
When used together with a [URL pattern](#url-pattern), named groups will be passed
as `kwargs`.

``` python
import httpx
import re
import respx


def some_content(request, slug=None):
    """ Return bytes, str, list or a dict. """
    return {"slug": slug}


@respx.mock
def test_something():
    url_pattern = r"^https://foo.bar/(?P<slug>\w+)/$")
    respx.get(url_pattern, content=some_content)

    response = httpx.get("https://foo.bar/apa/")
    assert response.json() == {"slug": "apa"}
```


### Request Error

To simulate a failing request, *like a connection error*, pass an `Exception` instance.
This is useful when you need to test proper `HTTPX` error handling in your app.

``` python
import httpx
import httpcore
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/", content=httpcore.ConnectTimeout())
    response = httpx.get("https://foo.bar/")  # Will raise
```

---

## Built-in Assertions

RESPX has the following build-in assertion checks:

> * **assert_all_mocked**  
>   Asserts that all captured `HTTPX` requests are mocked. Defaults to `True`.
> * **assert_all_called**  
>   Asserts that all mocked request patterns were called. Defaults to `True`.

Configure checks by using the `respx.mock` decorator / context manager *with* parentheses.

``` python
@respx.mock(assert_all_called=False)
def test_something(respx_mock):
    respx_mock.get("https://some.url/")  # OK
    respx_mock.get("https://foo.bar/")

    response = httpx.get("https://foo.bar/")
    assert response.status_code == 200
    assert respx_mock.calls.call_count == 1
```
``` python
with respx.mock(assert_all_mocked=False) as respx_mock:
    response = httpx.get("https://foo.bar/")  # OK
    assert response.status_code == 200
    assert respx_mock.calls.call_count == 1
```

!!! attention "Without Parentheses"
    When using the *global* scope `@respx.mock` decorator / context manager, `assert_all_called` is **disabled**.

---

## Call Statistics

The `respx` API includes a `.calls` object, containing captured (`request`, `response`) tuples and MagicMock's *bells and whistles*, i.e. `call_count`, `assert_called` etc.

Each mocked response *request pattern* has its own `.calls`, along with `.called` and `.call_count ` stats shortcuts.

To reset stats without stop mocking, use `respx.reset()`.

``` python
import httpx
import respx


@respx.mock
def test_something():
    request = respx.post("https://foo.bar/baz/", status_code=201)
    httpx.post("https://foo.bar/baz/")
    assert request.called
    assert request.call_count == 1

    respx.get("https://foo.bar/", alias="index")
    httpx.get("https://foo.bar/")
    assert respx.aliases["index"].called
    assert respx.aliases["index"].call_count == 1

    assert respx.calls.call_count == 2

    request, response = respx.calls[-1]
    assert request.method == "GET"
    assert response.status_code == 200

    respx.reset()
    assert len(respx.calls) == 0
    assert respx.calls.call_count == 0
```
