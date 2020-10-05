import asyncio
import re

import httpx
import pytest
import trio
from httpcore._backends.asyncio import AsyncioBackend
from httpcore._backends.trio import TrioBackend

import respx
from respx import MockTransport


@pytest.mark.asyncio
async def test_alias():
    async with MockTransport(assert_all_called=False) as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url, alias="foobar")
        assert "foobar" not in respx.aliases
        assert "foobar" in respx_mock.aliases
        assert respx_mock.aliases["foobar"].url == request.url
        assert respx_mock["foobar"].url == request.url


@pytest.mark.parametrize("Backend", [AsyncioBackend, TrioBackend])
def test_stats(Backend):
    @respx.mock
    async def test(backend):
        url = "https://foo.bar/1/"
        respx.get(re.compile("https://some.thing"))
        respx.delete("https://some.thing")

        foobar1 = respx.get(url, status_code=202, alias="get_foobar", content="get")
        foobar2 = respx.delete(url, status_code=200, alias="del_foobar", content="del")

        assert foobar1.called is False
        assert foobar1.call_count == len(foobar1.calls)
        assert foobar1.call_count == 0
        assert respx.stats.call_count == len(respx.calls)
        assert respx.stats.call_count == 0

        async with httpx.AsyncClient() as client:
            get_response = await client.get(url)
            del_response = await client.delete(url)

        assert foobar1.called is True
        assert foobar2.called is True
        assert foobar1.call_count == 1
        assert foobar2.call_count == 1

        _request, _response = foobar1.calls[-1]
        assert isinstance(_request, httpx.Request)
        assert isinstance(_response, httpx.Response)
        assert _request.method == "GET"
        assert _request.url == url
        assert _response.status_code == get_response.status_code == 202
        assert _response.content == get_response.content == b"get"
        assert id(_response) != id(get_response)  # TODO: Fix this?

        _request, _response = foobar2.calls[-1]
        assert isinstance(_request, httpx.Request)
        assert isinstance(_response, httpx.Response)
        assert _request.method == "DELETE"
        assert _request.url == url
        assert _response.status_code == del_response.status_code == 200
        assert _response.content == del_response.content == b"del"
        assert id(_response) != id(del_response)  # TODO: Fix this?

        assert respx.stats.call_count == 2
        assert respx.calls[0] == foobar1.calls[-1]
        assert respx.calls[1] == foobar2.calls[-1]

        alias = respx.aliases["get_foobar"]
        assert alias == foobar1
        assert alias.alias == foobar1.alias

        alias = respx.aliases["del_foobar"]
        assert alias == foobar2
        assert alias.alias == foobar2.alias

    backend = Backend()
    if isinstance(backend, TrioBackend):
        trio.run(test, backend)
    else:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(test(backend))
        finally:
            loop.close()
