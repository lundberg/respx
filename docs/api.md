# API Reference

## Router

### Configuration

Creates a mock `Router` instance, ready to be used as decorator/manager for activation.

> <code>respx.<strong>mock</strong>(assert_all_mocked=True, *assert_all_called=True, base_url=None*)</strong></code>
>
> **Parameters:**
>
> * **assert_all_mocked** - *(optional) bool - default: `True`*  
>   Asserts that all sent and captured `HTTPX` requests are routed and mocked.
> * **assert_all_called** - *(optional) bool - default: `True`*  
>   Asserts that all added and mocked routes were called when exiting context.  
>   If disabled, all non-routed requests will be auto mocked with status code `200`.
> * **base_url** - *(optional) str*  
>   Base URL to match, on top of each route specific pattern *and/or* side effect.
>
> **Returns:** `Router`

!!! tip "pytest"
    Use the `@pytest.mark.respx(...)` marker with these parameters to configure the `respx_mock` [pytest fixture](examples.md#built-in-marker).

!!! note "NOTE"
    When using the *default* mock router `respx.mock`, *without settings*, `assert_all_called` is **disabled**.


### .route()

Adds a new, *optionally named*, `Route` with given [patterns](#patterns) *and/or* [lookups](#lookups) combined, using the [AND](#and) operator.

> <code>respx.<strong>route</strong>(*\*patterns, name=None, \*\*lookups*)</strong></code>
>
> **Parameters:**
>
> * **patterns** - *(optional) args*  
>   One or more [pattern](#patterns) objects.
> * **lookups** - *(optional) kwargs*  
>   One or more [pattern](#patterns) keyword [lookups](#lookups), given as `<pattern>__<lookup>=value`.
> * **name** - *(optional) str*  
>   Name this route.
>
> **Returns:** `Route`

### .get(), .post(), ...

HTTP method helpers to add routes, mimicking the [HTTPX Helper Functions](https://www.python-httpx.org/api/#helper-functions).

> <code>respx.<strong>get</strong>(*url, name=None, \*\*lookups*)</strong></code>

> <code>respx.<strong>options</strong>(...)</strong></code>

> <code>respx.<strong>head</strong>(...)</strong></code>

> <code>respx.<strong>post</strong>(...)</strong></code>

> <code>respx.<strong>put</strong>(...)</strong></code>

> <code>respx.<strong>patch</strong>(...)</strong></code>

> <code>respx.<strong>delete</strong>(...)</strong></code>
>
> **Parameters:**
>
> * **url** - *(optional) str | compiled regex | tuple (httpcore) | httpx.URL*  
>   Request URL to match, *full or partial*, turned into a [URL](#url) pattern.
> * **name** - *(optional) str*  
>   Name this route.
> * **lookups** - *(optional) kwargs*  
>   One or more [pattern](#patterns) keyword [lookups](#lookups), given as `<pattern>__<lookup>=value`.
>
> **Returns:** `Route`
``` python
respx.get("https://example.org/", params={"foo": "bar"}, ...)
```

### .request()

> <code>respx.<strong>request</strong>(*method, url, name=None, \*\*lookups*)</strong></code>
>
> **Parameters:**
>
> * **method** - *str*  
>   Request HTTP method to match.
> * **url** - *(optional) str | compiled regex | tuple (httpcore) | httpx.URL*  
>   Request URL to match, *full or partial*, turned into a [URL](#url) pattern.
> * **name** - *(optional) str*  
>   Name this route.
> * **lookups** - *(optional) kwargs*  
>   One or more [pattern](#patterns) keyword [lookups](#lookups), given as `<pattern>__<lookup>=value`.
>
> **Returns:** `Route`
``` python
respx.request("GET", "https://example.org/", params={"foo": "bar"}, ...)
```

---

## Route

### .mock()

Mock a route's response or side effect.

> <code>route.<strong>mock</strong>(*return_value=None, side_effect=None*)</strong></code>
>
> **Parameters:**
>
> * **return_value** - *(optional) [Response](#response)*  
>   HTTPX Response to mock and return.
> * **side_effect** - *(optional) Callable | Exception | Iterable of httpx.Response/Exception*  
>   [Side effect](guide.md#mock-with-a-side-effect) to call, exception to raise or stacked responses to respond with in order.
>
> **Returns:** `Route`

### .return_value

Setter for the `HTTPX` [Response](#response) to return.

> <code>route.**return_value** = Response(204)</code>

### .side_effect

Setter for the [side effect](guide.md#mock-with-a-side-effect) to trigger.

> <code>route.**side_effect** = ...</code>
>
> See [route.mock()](#mock) for valid side effect types.

### .respond()

Shortcut for creating and mocking a `HTTPX` [Response](#response).

> <code>route.<strong>respond</strong>(*status_code=200, headers=None, content=None, text=None, html=None, json=None, stream=None*)</strong></code>
>
> **Parameters:**
>
> * **status_code** - *(optional) int - default: `200`*  
>   Response status code to mock.
> * **headers** - *(optional) dict*  
>   Response headers to mock.
> * **content** - *(optional) bytes | str | iterable bytes*  
>   Response raw content to mock.
> * **text** - *(optional) str*  
>   Response *text* content to mock, with automatic content-type header added.
> * **html** - *(optional) str*  
>   Response *HTML* content to mock, with automatic content-type header added.
> * **json** - *(optional) str | list | dict*  
>   Response *JSON* content to mock, with automatic content-type header added.
> * **stream** - *(optional) Iterable[bytes]*  
>   Response *stream* to mock.
>
> **Returns:** `Route`

### .pass_through()

> <code>route.<strong>pass_through</strong>(*value=True*)</strong></code>
>
> **Parameters:**
>
> * **value** - *(optional) bool - default: `True`*  
>   Mark route to pass through, sending matched requests to real server, *e.g. don't mock*.
>
> **Returns:** `Route`

---

## Response

!!! note "NOTE"
    This is a partial reference for how to the instantiate the **HTTPX** `Response`class, e.g. *not* a RESPX class.

> <code>httpx.<strong>Response</strong>(*status_code, headers=None, content=None, text=None, html=None, json=None, stream=None*)</strong></code>
>
> **Parameters:**
>
> * **status_code** - *int*  
>   HTTP status code.
> * **headers** - *(optional) dict | httpx.Headers*  
>   HTTP headers.
> * **content** - *(optional) bytes | str | Iterable[bytes]*  
>   Raw content.
> * **text** - *(optional) str*  
>   Text content, with automatic content-type header added.
> * **html** - *(optional) str*  
>   HTML content, with automatic content-type header added.
> * **json** - *(optional) str | list | dict*  
>   JSON content, with automatic content-type header added.
> * **stream** - *(optional) Iterable[bytes]*  
>   Content *stream*.

---

## Patterns

### M()

Creates a reusable pattern, combining multiple arguments using the [AND](#and) operator.

> <code><strong>M</strong>(*\*patterns, \*\*lookups*)</strong></code>
>
> **Parameters:**
>
> * **patterns** - *(optional) args*  
>   One or more [pattern](#patterns) objects.
> * **lookups** - *(optional) kwargs*  
>   One or more [pattern](#patterns) keyword [lookups](#lookups), given as `<pattern>__<lookup>=value`.
>
> **Returns:** `Pattern`
``` python
import respx
from respx.patterns import M
pattern = M(host="example.org")
respx.route(pattern)
```
> See [operators](#operators) for advanced usage.



### Method
Matches request *HTTP method*, using <code>[eq](#eq)</code> as default lookup.
> Key: `method`  
> Lookups: [eq](#eq), [in](#in)
``` python
respx.route(method="GET")
respx.route(method__in=["PUT", "PATCH"])
```

### Scheme
Matches request *URL scheme*, using <code>[eq](#eq)</code> as default lookup.
> Key: `scheme`  
> Lookups: [eq](#eq), [in](#in)
``` python
respx.route(scheme="https")
respx.route(scheme__in=["http", "https"])
```

### Host
Matches request *URL host*, using <code>[eq](#eq)</code> as default lookup.
> Key: `host`  
> Lookups: [eq](#eq), [regex](#regex), [in](#in)
``` python
respx.route(host="example.org")
respx.route(host__regex=r"example\.(org|com)")
respx.route(host__in=["example.org", "example.com"])
```

### Port
Matches request *URL port*, using <code>[eq](#eq)</code> as default lookup.
> Key: `port`  
> Lookups: [eq](#eq), [in](#in)

``` python
respx.route(port=8000)
respx.route(port__in=[2375, 2376])
```

### Path
Matches request *URL path*, using <code>[eq](#eq)</code> as default lookup.
> Key: `path`  
> Lookups: [eq](#eq), [regex](#regex), [startswith](#startswith), [in](#in)
``` python
respx.route(path="/api/foobar/")
respx.route(path__regex=r"^/api/(?P<slug>\w+)/")
respx.route(path__startswith="/api/")
respx.route(path__in=["/api/v1/foo/", "/api/v2/foo/"])
```

### Params
Matches request *URL query params*, using <code>[contains](#contains)</code> as default lookup.
> Key: `params`  
> Lookups: [contains](#contains), [eq](#eq)
``` python
respx.route(params={"foo": "bar", "ham": "spam"})
respx.route(params=[("foo", "bar"), ("ham", "spam")])
respx.route(params="foo=bar&ham=spam")
```

### URL
Matches request *URL*.

When no *lookup* is given, `url` works as a *shorthand* pattern, combining individual request *URL* parts, using the [AND](#and) operator.
> Key: `url`  
> Lookups: [eq](#eq), [regex](#regex), [startswith](#startswith)
``` python
respx.get("//example.org/foo/")  # == M(host="example.org", path="/foo/")
respx.get(url__eq="https://example.org:8080/foobar/?ham=spam")
respx.get(url__regex=r"https://example.org/(?P<slug>\w+)/")
respx.get(url__startswith="https://example.org/api/")
respx.get("all://*.example.org/foo/")
```

### Content
Matches request raw *content*, using [eq](#eq) as default lookup.
> Key: `content`  
> Lookups: [eq](#eq)
``` python
respx.post("https://example.org/", content="foobar")
respx.post("https://example.org/", content=b"foobar")
```

### Data
Matches request *form data*, using [eq](#eq) as default lookup.
> Key: `data`  
> Lookups: [eq](#eq)
``` python
respx.post("https://example.org/", data={"foo": "bar"})
```

### JSON
Matches request *json* content, using [eq](#eq) as default lookup.
> Key: `json`  
> Lookups: [eq](#eq)
``` python
respx.post("https://example.org/", json={"foo": "bar"})
```
The `json` pattern also supports path traversing, *i.e.* `json__<path>=<value>`.
``` python
respx.post("https://example.org/", json__foobar__0__ham="spam")
httpx.post("https://example.org/", json={"foobar": [{"ham": "spam"}]})
```

### Headers
Matches request *headers*, using [contains](#contains) as default lookup.
> Key: `headers`  
> Lookups: [contains](#contains), [eq](#eq)
``` python
respx.route(headers={"foo": "bar", "ham": "spam"})
respx.route(headers=[("foo", "bar"), ("ham", "spam")])
```

### Cookies
Matches request *cookie header*, using [contains](#contains) as default lookup.
> Key: `cookies`  
> Lookups: [contains](#contains), [eq](#eq)
``` python
respx.route(cookies={"foo": "bar", "ham": "spam"})
respx.route(cookies=[("foo", "bar"), ("ham", "spam")])
```

## Lookups

### eq

``` python
M(path="/foo/bar/")
M(path__eq="/foo/bar/")
```

### contains
Case-sensitive containment test.
``` python
M(params__contains={"id": "123"})
```

### in
Case-sensitive within test.
``` python
M(method__in=["PUT", "PATCH"])
```

### regex
``` python
M(path__regex=r"^/api/(?P<slug>\w+)/")
```

### startswith
Case-sensitive starts-with.
``` python
M(path__startswith="/api/")
```

## Operators

Patterns can be combined using bitwise operators, creating new patterns.

### AND (&)
Combines two `Pattern`s using `and` operator.
``` python
M(scheme="http") & M(host="example.org")
```

### OR (&)
Combines two `Pattern`s using `or` operator.
``` python
M(method="PUT") | M(method="PATCH")
```

### INVERT (~)
Inverts a `Pattern` match.
``` python
~M(params={"foo": "bar"})
```
