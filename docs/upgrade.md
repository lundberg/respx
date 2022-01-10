# Upgrade Guide

As of RESPX version `0.15.0`, the API has changed, but kept with **deprecation** warnings, later to be **broken** for backward compatibility in `0.16.0`.

The biggest change involved *separating* request pattern *arguments* from response details.

This brings the RESPX request matching API closer to the `HTTPX` client API, and the response mocking aligned with the python `Mock` API.

## Responses
Response details are now mocked separatelty:
``` python
# Previously
respx.post("https://some.url/", status_code=200, content={"x": 1})

# Now
respx.post("https://some.url/").mock(return_value=Response(200, json={"x": 1}))
respx.post("https://some.url/").respond(200, json={"x": 1})
respx.post("https://some.url/") % dict(json={"x": 1})
```

The `.add` API has changed to `.route`:
``` python
# Previously
respx.add("POST", "https://some.url/", content="foobar")

# Now
respx.route(method="POST", url="https://some.url/").respond(content="foobar")
```

## Callbacks
Callbacks and simulated errors are now *side effects*:
``` python
# Previously
respx.post("https://some.url/", content=callback)
respx.post("https://some.url/", content=Exception())
respx.add(callback)

# Now
respx.post("https://some.url/").mock(side_effect=callback)
respx.post("https://some.url/").mock(side_effect=Exception)
respx.route().mock(side_effect=callback)
```

## Stacking
Repeating a mocked response, for stacking, is now solved with *side effects*:
``` python
# Previously
respx.post("https://some.url/", status_code=404)
respx.post("https://some.url/", status_code=200)

# Now
respx.post("https://some.url/").mock(
    side_effect=[
        Response(404),
        Response(200),
    ],
)
```
> **Note:** Repeating a route in `0.15.0+` replaces any existing route with same pattern.

## Aliasing
Aliases changed to *named routes*:
``` python
# Previously
respx.post("https://example.org/", alias="example")
assert respx.aliases["example"].called

# Now
respx.post("https://example.org/", name="example")
assert respx.routes["example"].called
```

## History
Call history *renamed*:
``` python
# Previously
assert respx.stats.call_count == 1

# Now
assert respx.calls.call_count == 1
```

## MockTransport
The `respx.MockTransport` should no longer be used as a mock router, use `respx.mock(...)`.
``` python
# Previously
my_mock = respx.MockTransport(assert_all_called=False)

# Now
my_mock = respx.mock(assert_all_called=False)
```
