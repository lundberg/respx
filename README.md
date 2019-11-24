# RESPX

![](https://github.com/lundberg/respx/workflows/test/badge.svg)
[![codecov](https://codecov.io/gh/lundberg/respx/branch/master/graph/badge.svg)](https://codecov.io/gh/lundberg/respx)
[![PyPi Version](https://img.shields.io/pypi/v/respx.svg)](https://pypi.org/project/respx/)
[![Python Versions](https://img.shields.io/pypi/pyversions/respx.svg)](https://pypi.org/project/respx/)

A utility for mocking out the Python [HTTPX](https://github.com/encode/httpx) library.

## Usage

For starters, you need to mock `HTTPX`, by using the `RESPX` **decorator** or **context managers**.


## Decorator

```py
import httpx
import respx


@respx.mock
def test_something():
    request = respx.post("https://foo.bar/baz/", status_code=201)
    response = httpx.post("https://foo.bar/baz/")
    assert request.called
    assert response.status_code == 201


@respx.mock(assert_all_mocked=False)
def test_something(httpx_mock):
    response = httpx.post("https://foo.bar/baz/")
    assert response.status_code == 200

```


## Context Manager

```py
import httpx
import respx


with respx.mock:
    request = respx.get("https://foo.bar/", content={"foo": "bar"})
    response = httpx.get("https://foo.bar/")
    assert request.called
    assert response.json() == {"foo": "bar"}


with respx.mock(assert_all_called=False) as httpx_mock:
    httpx_mock.get("https://ham.spam/")
    request = httpx_mock.get("https://foo.bar/", content={"foo": "bar"})
    response = httpx.get("https://foo.bar/")
    assert request.called
    assert response.json() == {"foo": "bar"}
```

> **NOTE:** You can also start and stop mocking `HTTPX` manually, by calling `respx.start()` and `respx.stop()`


## Mocking responses

To mock a response, define the *request pattern* to match and the *response details* to return.

For regular and simple use, use the HTTP method shorthands:

**`respx.get`**(*url=None, status_code=None, content=None, content_type=None, headers=None, pass_through=False, alias=None*) -> RequestPattern

**`respx.options`**(*url=None, ...*)

**`respx.head`**(*url=None, ...*)

**`respx.post`**(*url=None, ...*)

**`respx.put`**(*url=None, ...*)

**`respx.patch`**(*url=None, ...*)

**`respx.delete`**(*url=None, ...*)

For advanced use:

**`respx.request`**(*method, url=None, status_code=None, content=None, content_type=None, headers=None, pass_through=False, alias=None*) -> RequestPattern

### Parameters

> * **method** - *str | callable*  
>   * Request HTTP method to match - GET, OPTIONS, HEAD, POST, PUT, PATCH or DELETE.
>   * Request match callback. *See [Custom request matching](#custom-request-matching).*
> * **url** - *(optional) str | pattern*  
>   * Request URL exact string to match.
>   * Request URL pattern to match. *See [URL pattern matching](#url-pattern-matching).*
> * **status_code** - *(optional) int*  
>   Response status code. [Default: 200]
> * **content** - *(optional) bytes | str | list | dict | callable | exception*  
>   Response content. [Default: b""] - *See [JSON content](#json-content), [Content callback](#content-callback).*
> * **content_type** - *(optional) str*  
>   Response Content-Type header value. [Default: text/plain]
> * **headers** - *(optional) dict*  
>   Response headers.
> * **pass_through** - *(optional) bool*  
>   Mark request to pass-through to real server, e.g. don't mock. [Default: False]
> * **alias** - *(optional) str*  
>   Name this request pattern. - *See [Call stats](#call-stats).*


## URL pattern matching

Instead of matching an exact URL, you can pass a *compiled regex* to match the request URL.

```py
import httpx
import re
import respx


@respx.mock
def test_something():
    respx.get(re.compile(r"^https://foo.bar/.*$"), content="Baz")
    response = httpx.get("https://foo.bar/baz/")
    assert response.text == "Baz"
```
> **NOTE:** Named groups in the pattern will be passed as `kwargs` to [content callback](#content-callback), if used.


## JSON content

To mock a response with json content, pass a `list` or `dict`. The `Content-Type` header will be set to `application/json`.

```py
import httpx
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/baz/123/", content={"id": 123})
    response = httpx.get("https://foo.bar/baz/123/")
    assert response.json() == {"id": 123}
```

## Content callback

If you need dynamic response content, use a callback function as the `content` parameter.

```py
import httpx
import re
import respx


def baz_content(request, pk=None):
    """
    If a URL pattern were used, named groups will be passed as optional kwargs.
    
    Return bytes, str, list or a dict.
    """
    return {"id": int(pk)}


@respx.mock
def test_something():
    respx.get(re.compile(r"^https://foo.bar/baz/(?P<pk>\d+)/$"), content=baz_content)
    response = httpx.get("https://foo.bar/baz/123/")
    assert response.json() == {"id": 123}
```


## Mock a request exception

To simulate a request problem, *like a connection error*, pass an `Exception` instance as the `content` parameter.

```py
import httpx
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/", content=httpx.ConnectTimeout())
    response = httpx.get("https://foo.bar/")  # Will raise
```


## Custom request matching

For full control of what to *match* and what response to *mock*, pass a callback function as the `method` parameter.

```py
import httpx
import respx


def custom_matcher(request, response):
    """
    Response object is populated with any given response parameters from the respx.request(...) call.

    Return None to not match.
    Return the response for a match and to mock this request.
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


## Repeated patterns

If you mock several responses with the same request pattern, they will be matched in order, and popped til the last one.

```py
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


## Built-in assertions

RESPX has the following build-in assertion checks:

> * **assert_all_mocked**  
>   Asserts that all captured `HTTPX` requests are mocked.
> * **assert_all_called**  
>   Asserts that all mocked request patterns were called.

When using the *global* `respx.mock` decorator/manager, `assert_all_called` is **disabled**.  
When using the *local* `respx.mock(...)` decorator/manager, both checks is, by default, **enabled**.

```py
with respx.mock(assert_all_called=False, assert_all_mocked=False) as httpx_mock:
    response = httpx.get("https://foo.bar/")  # Will not raise AssersionError, but instead auto mock.
    assert response.status_code == 200
    assert httpx_mock.stats.call_count == 1
```


## Call stats

The global `respx` api has a `.calls` list, containing captured (`request`, `response`) tuples. On top of that there's also a *MagicMock* `.stats` object with all its bells and whistles, i.e. `call_count`, `assert_called_once` etc.

Request patterns has their own `.calls` and `.stats`, along with shortcuts to stats`.called` and `.call_count`.

```py
import httpx
import respx


@respx.mock
def test_something():
    respx.get("https://foo.bar/", alias="index")  # Aliased request pattern
    create_request = respx.post("https://foo.bar/baz/")
    put_request = respx.put("https://foo.bar/baz/123/", status_code=202)
    
    httpx.get("https://foo.bar/")
    index_request = respx.aliases["index"]  # Alias
    assert index_request.called
    assert index_request.call_count == 1

    httpx.post("https://foo.bar/baz/")
    assert create_request.called
    assert create_request.call_count == 1

    httpx.put("https://foo.bar/baz/123/")
    assert put_request.called
    assert put_request.call_count == 1
    
    assert respx.stats.call_count == 3
    
    request, response = respx.calls[-1]
    assert request.method == "PUT"
    assert response.status_code == 202
```
