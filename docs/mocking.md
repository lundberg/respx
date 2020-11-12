# Mock HTTPX

RESPX is a mock router, [capturing](guide.md#mock-httpx) requests sent by `HTTPX`, [mocking](guide.md#mocking-responses) their responses.

Inspired by the flexible query API of the [Django](https://www.djangoproject.com/) ORM, requests are filtered and matched against routes and their request [patterns](api.md#patterns) and [lookups](api.md#lookups).

Request [patterns](api.md#patterns) are *bits* of the request, like `host` `method` `path` etc, 
with given [lookup](api.md#lookups) values, combined using *bitwise* [operators](api.md#operators) to form a `Route`,
i.e. `respx.route(path__regex=...)`

A captured request, [matching](guide.md#routing-requests) a `Route`, resolves to a [mocked](guide.md#mock-a-response) `httpx.Response`, or triggers a given [side effect](guide.md#mock-with-a-side-effect).
To skip mocking a specific request, a route can be marked to [pass through](guide.md#pass-through).

> Read the [User Guide](guide.md) for a complete walk-through.
