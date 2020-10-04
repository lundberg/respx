import httpcore
import httpx
import pytest

from respx import AsyncMockTransport, MockTransport, SyncMockTransport


def test_sync_transport():
    url = "https://foo.bar/"

    transport = SyncMockTransport(assert_all_called=False)
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

    transport = AsyncMockTransport(assert_all_called=False)
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

    transport = AsyncMockTransport()
    transport.get(url, status_code=404)
    transport.post(url, content={"foo": "bar"})

    with pytest.raises(AssertionError, match="not called"):
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get(url)
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_httpcore_request():
    async with MockTransport() as transport:
        transport.add("GET", "https://foo.bar/", content="foobar")
        with httpcore.SyncConnectionPool() as http:
            (status_code, headers, stream, ext) = http.request(
                method=b"GET", url=(b"https", b"foo.bar", 443, b"/")
            )

            body = b"".join([chunk for chunk in stream])
            stream.close()
            assert body == b"foobar"

        async with httpcore.AsyncConnectionPool() as http:
            (status_code, headers, stream, ext) = await http.arequest(
                method=b"GET", url=(b"https", b"foo.bar", 443, b"/")
            )

            body = b"".join([chunk async for chunk in stream])
            await stream.aclose()
            assert body == b"foobar"


def test_transport_pop():
    url = "https://foo.bar/"
    alias = "get_alias"

    transport = AsyncMockTransport()
    transport.get(url, status_code=404, alias=alias)

    request_pattern = transport.pop(alias)

    assert request_pattern.response.status_code == 404
    assert request_pattern.alias == alias
    assert str(request_pattern.url._url) == url

    assert not transport.aliases
    assert not transport.patterns

    with pytest.raises(KeyError):
        transport.pop(alias)

    assert transport.pop(alias, "custom default") == "custom default"
