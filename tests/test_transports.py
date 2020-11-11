import httpcore
import httpx
import pytest

from respx import MockTransport
from respx.transports import RouterTransport


def test_sync_transport():
    url = "https://foo.bar/"

    transport = RouterTransport(assert_all_called=False)
    transport.get(url) % 404
    transport.post(url).pass_through()
    transport.put(url)

    with httpx.Client(transport=transport) as client:
        response = client.get(url)
        assert response.status_code == 404
        with pytest.raises(ValueError, match="pass_through"):
            client.post(url)


@pytest.mark.asyncio
async def test_async_transport():
    url = "https://foo.bar/"

    transport = RouterTransport(assert_all_called=False)
    transport.get(url) % 404
    transport.post(url).pass_through()
    transport.put(url)

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(url)
        assert response.status_code == 404
        with pytest.raises(ValueError, match="pass_through"):
            await client.post(url)


@pytest.mark.asyncio
async def test_transport_assertions():
    url = "https://foo.bar/"

    transport = RouterTransport(assert_all_called=True)
    transport.get(url) % 404
    transport.post(url) % dict(json={"foo": "bar"})

    with pytest.raises(AssertionError, match="were not called"):
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get(url)
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_httpcore_request():
    async with MockTransport() as transport:
        for url, port in [("https://foo.bar/", None), ("https://foo.bar:443/", 443)]:
            transport.route(method="GET", url=url) % dict(text="foobar")
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

    transport = MockTransport()
    transport.get(url, name=name) % 404

    route = transport.pop(name)

    assert route.resolve(httpx.Request("GET", "https://foo.bar/")).status_code == 404
    assert route.name == name

    assert not transport.routes

    with pytest.raises(KeyError):
        transport.pop(name)

    assert transport.pop(name, "custom default") == "custom default"
