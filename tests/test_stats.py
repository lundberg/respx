import re

import httpx
import pytest

import respx
from respx.router import MockRouter


@pytest.mark.asyncio
async def test_named_route():
    async with MockRouter(assert_all_called=False) as respx_mock:
        request = respx_mock.get("https://foo.bar/", name="foobar")
        assert "foobar" not in respx.routes
        assert "foobar" in respx_mock.routes
        assert respx_mock.routes["foobar"] is request
        assert respx_mock["foobar"] is request


@respx.mock
async def backend_test(backend):
    url = "https://foo.bar/1/"
    respx.get(re.compile("https://some.thing"))
    respx.delete("https://some.thing")

    foobar1 = respx.get(url, name="get_foobar") % dict(status_code=202, text="get")
    foobar2 = respx.delete(url, name="del_foobar") % dict(text="del")

    assert foobar1.called is False
    assert foobar1.call_count == len(foobar1.calls)
    assert foobar1.call_count == 0
    assert foobar1.calls.last is None
    assert respx.calls.call_count == len(respx.calls)
    assert respx.calls.call_count == 0

    async with httpx.AsyncClient() as client:
        get_response = await client.get(url)
        del_response = await client.delete(url)

    assert foobar1.called is True
    assert foobar2.called is True
    assert foobar1.call_count == 1
    assert foobar2.call_count == 1
    assert foobar1.calls.call_count == 1

    _request, _response = foobar1.calls[-1]
    assert isinstance(_request, httpx.Request)
    assert isinstance(_response, httpx.Response)
    assert foobar1.calls.last.request is _request
    assert foobar1.calls.last.response is _response
    assert _request.method == "GET"
    assert _request.url == url
    assert _response.status_code == get_response.status_code == 202
    assert _response.content == get_response.content == b"get"
    assert {
        _response.status_code,
        tuple(_response.headers.raw),
        _response.stream,
        tuple(_response.ext.items()),
    } == {
        get_response.status_code,
        tuple(get_response.headers.raw),
        get_response.stream,
        tuple(get_response.ext.items()),
    }
    assert id(_response) != id(get_response)

    _request, _response = foobar2.calls[-1]
    assert isinstance(_request, httpx.Request)
    assert isinstance(_response, httpx.Response)
    assert _request.method == "DELETE"
    assert _request.url == url
    assert _response.status_code == del_response.status_code == 200
    assert _response.content == del_response.content == b"del"
    assert {
        _response.status_code,
        tuple(_response.headers.raw),
        _response.stream,
        tuple(_response.ext.items()),
    } == {
        del_response.status_code,
        tuple(del_response.headers.raw),
        del_response.stream,
        tuple(del_response.ext.items()),
    }
    assert id(_response) != id(del_response)

    assert respx.calls.call_count == 2
    assert respx.calls[0] == foobar1.calls[-1]
    assert respx.calls[1] == foobar2.calls[-1]

    assert respx.mock.calls.call_count == 2
    assert respx.calls.call_count == 2

    route = respx.routes["get_foobar"]
    assert route == foobar1
    assert route.name == foobar1.name

    route = respx.routes["del_foobar"]
    assert route == foobar2
    assert route.name == foobar2.name


def test_asyncio():
    import asyncio

    from httpcore._backends.asyncio import AsyncioBackend

    backend = AsyncioBackend()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(backend_test(backend))
    finally:
        loop.close()


def test_trio():  # pragma: nocover
    import trio
    from httpcore._backends.trio import TrioBackend

    backend = TrioBackend()
    trio.run(backend_test, backend)
