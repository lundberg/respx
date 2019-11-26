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


### Request API

For full control, use the core request method.

> ::: respx.request
>     :docstring:
>
> **Parameters:**
>
> * **method** - *str | callable*  
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

### URL pattern

Instead of matching an exact URL, you can pass a *compiled regex* to match the request URL.

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


### Request callback

For full control of what request to **match** and what response to **mock**, pass a callback function as the request `method` parameter.

``` python
import httpx
import respx


def custom_matcher(request, response):
    """
    Response argument is pre-populated with any given
    response parameters from the respx.request(...) call.

    Return `None` to not match the request.
    Return the response to match and mock this request.
    Return the request for pass-through behaviour.
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
    custom_request = respx.request(custom_matcher, status_code=201)
    respx.get("https://foo.bar/baz/")

    response = httpx.get("https://foo.bar/baz/")
    assert response.status_code == 200
    assert not custom_request.called

    response = httpx.post("https://foo.bar/baz/")
    assert response.status_code == 401
    assert custom_request.called

    response = httpx.post("https://foo.bar/baz/", headers={"X-Auth-Token": "token"})
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

If you need dynamic response content, pass a callback function.

``` python
import httpx
import re
import respx


def my_content(request, slug=None):
    """
    Named groups in a URL pattern will be passed kwargs.

    Return bytes, str, list or a dict.
    """
    return {"slug": slug}


@respx.mock
def test_something():
    url_pattern = r"^https://foo.bar/(?P<slug>\w+)/$")
    respx.get(url_pattern, content=my_content)

    response = httpx.get("https://foo.bar/apa/")
    assert response.json() == {"slug": "apa"}
```


### Request Error

To simulate a failing request, *like a connection error*, pass an `Exception` instance.
This is useful when you need to test proper `HTTPX` error handling in your app.

``` python
import httpx
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/", content=httpx.ConnectTimeout())
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
def test_something(httpx_mock):
    httpx_mock.get("https://some.url/")  # Will not cause assertion fail
    httpx_mock.get("https://foo.bar/")

    response = httpx.get("https://foo.bar/")
    assert response.status_code == 200
    assert httpx_mock.stats.call_count == 1
```
``` python
with respx.mock(assert_all_mocked=False) as httpx_mock:
    response = httpx.get("https://foo.bar/")  # Will cause assertion fail
    assert response.status_code == 200
    assert httpx_mock.stats.call_count == 1
```

!!! attention "Without Parentheses"
    When using the *global* scope `@respx.mock` decorator / context manager, `assert_all_called` is **disabled**.

---

## Call Statistics

The `respx` API includes a `.calls` list, containing captured (`request`, `response`) tuples, and a `.stats` MagicMock object with all its *bells and whistles*, i.e. `call_count`, `assert_called` etc.

Each mocked response *request pattern* has its own `.calls` and `.stats`, along with `.called` and `.call_count ` stats shortcuts.

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

    assert respx.stats.call_count == 2

    request, response = respx.calls[-1]
    assert request.method == "GET"
    assert response.status_code == 200
```