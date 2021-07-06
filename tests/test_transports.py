import warnings

import httpx
import pytest

from respx.models import PassThrough
from respx.router import Router
from respx.transports import MockTransport


def test_sync_transport_handler():
    url = "https://foo.bar/"

    router = Router(assert_all_called=False)
    router.get(url) % 404
    router.post(url).pass_through()
    router.put(url)

    with warnings.catch_warnings(record=True) as w:
        transport = MockTransport(handler=router.handler)
        assert len(w) == 1

    with httpx.Client(transport=transport) as client:
        response = client.get(url)
        assert response.status_code == 404
        with pytest.raises(PassThrough):
            client.post(url)


@pytest.mark.asyncio
async def test_async_transport_handler():
    url = "https://foo.bar/"

    router = Router(assert_all_called=False)
    router.get(url) % 404
    router.post(url).pass_through()
    router.put(url)

    with warnings.catch_warnings(record=True) as w:
        transport = MockTransport(async_handler=router.async_handler)
        assert len(w) == 1

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(url)
        assert response.status_code == 404
        with pytest.raises(PassThrough):
            await client.post(url)


@pytest.mark.asyncio
async def test_transport_assertions():
    url = "https://foo.bar/"

    router = Router(assert_all_called=True)
    router.get(url) % 404
    router.post(url) % dict(json={"foo": "bar"})

    with warnings.catch_warnings(record=True) as w:
        transport = MockTransport(router=router)
        assert len(w) == 1

    with pytest.raises(AssertionError, match="were not called"):
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get(url)
            assert response.status_code == 404


def test_required_kwarg():
    with pytest.raises(RuntimeError, match="argument"):
        MockTransport()
