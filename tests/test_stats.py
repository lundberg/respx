import asyncio
import re

import asynctest
import httpx
import pytest
import trio
from httpx.backends.asyncio import AsyncioBackend
from httpx.backends.trio import TrioBackend

import respx


@pytest.mark.asyncio
async def test_alias():
    async with respx.HTTPXMock(assert_all_called=False) as httpx_mock:
        url = "https://foo.bar/"
        request = httpx_mock.get(url, alias="foobar")
        assert "foobar" not in respx.aliases
        assert "foobar" in httpx_mock.aliases
        assert httpx_mock.aliases["foobar"].url == request.url
        assert httpx_mock["foobar"].url == request.url


@pytest.mark.asyncio
async def test_httpx_exception_handling(client):
    async with respx.HTTPXMock() as httpx_mock:
        with asynctest.mock.patch(
            "httpx.client.AsyncClient.dispatcher_for_url",
            side_effect=ValueError("mock"),
        ):
            url = "https://foo.bar/"
            request = httpx_mock.get(url)
            with pytest.raises(ValueError):
                await client.get(url)

        assert request.called is True
        assert httpx_mock.stats.call_count == 1
        _request, _response = httpx_mock.calls[-1]
        assert _request is not None
        assert _response is None


@pytest.mark.parametrize("Backend", [AsyncioBackend, TrioBackend])
def test_stats(Backend):
    @respx.mock
    async def test(backend):
        url = "https://foo.bar/1/"
        respx.get(re.compile("https://some.thing"))
        respx.delete("https://some.thing")

        foobar1 = respx.get(url, status_code=202, alias="get_foobar")
        foobar2 = respx.delete(url, status_code=200, alias="del_foobar")

        assert foobar1.called is False
        assert foobar1.call_count == len(foobar1.calls)
        assert foobar1.call_count == 0
        assert respx.stats.call_count == len(respx.calls)
        assert respx.stats.call_count == 0

        async with httpx.AsyncClient(backend=backend) as client:
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
        assert _response.status_code == 202
        assert _response.status_code == get_response.status_code
        assert _response.content == get_response.content
        assert id(_response) == id(get_response)

        _request, _response = foobar2.calls[-1]
        assert isinstance(_request, httpx.Request)
        assert isinstance(_response, httpx.Response)
        assert _request.method == "DELETE"
        assert _request.url == url
        assert _response.status_code == 200
        assert _response.status_code == del_response.status_code
        assert _response.content == del_response.content
        assert id(_response) == id(del_response)

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
