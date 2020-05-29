import httpx
import pytest

from respx import AsyncMockTransport, SyncMockTransport


def test_sync_transport():
    url = "https://foo.bar/"

    transport = SyncMockTransport()
    transport.get(url, status_code=404)
    transport.get(url, content={"foo": "bar"})
    transport.post(url, pass_through=True)

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

    transport = AsyncMockTransport()
    transport.get(url, status_code=404)
    transport.get(url, content={"foo": "bar"})
    transport.post(url, pass_through=True)

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(url)
        assert response.status_code == 404
        response = await client.get(url)
        assert response.status_code == 200
        assert response.json() == {"foo": "bar"}
        with pytest.raises(ValueError, match="pass_through"):
            await client.post(url)
