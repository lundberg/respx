import warnings

import httpcore
import httpx
import pytest

from respx import AsyncMockTransport, MockTransport, SyncMockTransport


def test_sync_transport():
    url = "https://foo.bar/"

    with warnings.catch_warnings(record=True) as w:
        transport = SyncMockTransport(assert_all_called=False)
        assert len(w) == 1
    transport.get(url, status_code=404)
    transport.get(url, content={"foo": "bar"})
    transport.post(url, pass_through=True)
    transport.put(url)

    with httpx.Client(transport=transport) as client:
        response = client.get(url)
        assert response.status_code == 404
        response = client.get(url)
        assert response.status_code == 200
        assert response.json() == {"foo": "bar"}
        with pytest.raises(ValueError, match="pass_through"):
            client.post(url)


@pytest.mark.asyncio
async def test_async_transport():
    url = "https://foo.bar/"

    with warnings.catch_warnings(record=True) as w:
        transport = AsyncMockTransport(assert_all_called=False)
        assert len(w) == 1
    transport.get(url, status_code=404)
    transport.get(url, content={"foo": "bar"})
    transport.post(url, pass_through=True)
    transport.put(url)

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(url)
        assert response.status_code == 404
        response = await client.get(url)
        assert response.status_code == 200
        assert response.json() == {"foo": "bar"}
        with pytest.raises(ValueError, match="pass_through"):
            await client.post(url)


@pytest.mark.asyncio
async def test_transport_assertions():
    url = "https://foo.bar/"

    with warnings.catch_warnings(record=True) as w:
        transport = AsyncMockTransport()
        assert len(w) == 1
    transport.get(url, status_code=404)
    transport.post(url, content={"foo": "bar"})

    with pytest.raises(AssertionError, match="not called"):
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get(url)
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_httpcore_request():
    async with MockTransport() as transport:
        for url, port in [("https://foo.bar/", None), ("https://foo.bar:443/", 443)]:
            transport.add("GET", url, content="foobar")
            with httpcore.SyncConnectionPool() as http:
                (status_code, headers, stream, ext) = http.request(
                    method=b"GET", url=(b"https", b"foo.bar", port, b"/")
                )

                body = b"".join([chunk for chunk in stream])
                assert body == b"foobar"

            async with httpcore.AsyncConnectionPool() as http:
                (status_code, headers, stream, ext) = await http.arequest(
                    method=b"GET", url=(b"https", b"foo.bar", port, b"/")
                )

                body = b"".join([chunk async for chunk in stream])
                assert body == b"foobar"


@pytest.mark.asyncio
async def test_transport_pop():
    url = "https://foo.bar/"
    name = "ny_named_route"

    with warnings.catch_warnings(record=True) as w:
        transport = AsyncMockTransport()
        assert len(w) == 1
    transport.get(url, status_code=404, name=name)

    request_pattern = transport.pop(name)

    assert request_pattern.get_response().status_code == 404
    assert request_pattern.name == name

    assert not transport.aliases
    assert not transport.routes

    with pytest.raises(KeyError):
        transport.pop(name)

    assert transport.pop(name, "custom default") == "custom default"
