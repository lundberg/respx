import re
from contextlib import ExitStack as does_not_raise

import httpx
import pytest

import respx


@pytest.mark.asyncio
@respx.mock
async def test_decorating_test(client):
    assert respx.stats.call_count == 0
    request = respx.get("https://foo.bar/", status_code=202)
    response = await client.get("https://foo.bar/")
    assert request.called is True
    assert response.status_code == 202
    assert respx.stats.call_count == 1


@pytest.mark.asyncio
async def test_mock_fixture(client, httpx_mock):
    assert respx.stats.call_count == 0
    assert httpx_mock.stats.call_count == 0
    request = httpx_mock.get("https://foo.bar/", status_code=202)
    response = await client.get("https://foo.bar/")
    assert request.called is True
    assert response.status_code == 202
    assert respx.stats.call_count == 0
    assert httpx_mock.stats.call_count == 1


def test_global_sync_decorator():
    @respx.mock
    def test():
        assert respx.stats.call_count == 0
        request = respx.get("https://foo.bar/", status_code=202)
        response = httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_global_async_decorator(client, future):
    @respx.mock
    async def test():
        assert respx.stats.call_count == 0
        request = respx.get("https://foo.bar/", status_code=202)
        response = await client.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    await test()
    assert respx.stats.call_count == 0


def test_local_sync_decorator():
    @respx.mock()
    def test(httpx_mock):
        assert respx.stats.call_count == 0
        request = httpx_mock.get("https://foo.bar/", status_code=202)
        response = httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_local_async_decorator(client):
    @respx.mock()
    async def test(httpx_mock):
        assert respx.stats.call_count == 0
        request = httpx_mock.get("https://foo.bar/", status_code=202)
        response = await client.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    await test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_global_contextmanager(client):
    with respx.mock:
        assert respx.stats.call_count == 0
        request = respx.get("https://foo/bar/", status_code=202)
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    async with respx.mock:
        assert respx.stats.call_count == 0
        request = respx.get("https://foo/bar/", status_code=202)
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_local_contextmanager(client):
    with respx.mock() as httpx_mock:
        assert httpx_mock.stats.call_count == 0
        request = httpx_mock.get("https://foo/bar/", status_code=202)
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    async with respx.mock() as httpx_mock:
        assert httpx_mock.stats.call_count == 0
        request = httpx_mock.get("https://foo/bar/", status_code=202)
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    assert respx.stats.call_count == 0


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_nested_contextmanager(client):
    """
    with respx.mock() as httpx_mock_1:
        get_request = httpx_mock_1.get("https://foo/bar/", status_code=202)

        with respx.mock() as httpx_mock_2:
            post_request = httpx_mock_2.post("https://foo/bar/", status_code=201)

            response = await client.get("https://foo/bar/")
            assert get_request.called is True
            assert response.status_code == 202
            assert respx.stats.call_count == 1

            response = await client.post("https://foo/bar/")
            assert post_request.called is True
            assert response.status_code == 201
            assert respx.stats.call_count == 2
    """


@pytest.mark.asyncio
async def test_configured_decorator(client):
    @respx.mock(assert_all_called=False, assert_all_mocked=False)
    async def test(httpx_mock):
        assert httpx_mock.stats.call_count == 0
        request = httpx_mock.get("https://foo.bar/")
        response = await client.get("https://some.thing/")

        assert response.status_code == 200
        assert response.headers == httpx.Headers({"Content-Type": "text/plain"})
        assert response.text == ""

        assert request.called is False
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

        _request, _response = httpx_mock.calls[-1]
        assert _request is not None
        assert _response is not None
        assert _request.url == "https://some.thing/"

    await test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_base_url():
    async with respx.mock(base_url="https://foo.bar/") as httpx_mock:
        request1 = httpx_mock.get("/baz/", content="baz")
        request2 = httpx_mock.post(re.compile(r"(?P<slug>\w+)/?$"), content="slug")
        request3 = httpx_mock.put(content="ok")

        async with httpx.AsyncClient(base_url="https://foo.bar") as client:
            response = await client.get("/baz/")
            assert request1.called is True
            assert response.text == "baz"

            response = await client.post("/apa/")
            assert request2.called is True
            assert response.text == "slug"

            response = await client.put("/")
            assert request3.called is True
            assert response.text == "ok"


@pytest.mark.asyncio
async def test_start_stop(client):
    url = "https://foo.bar/"
    request = respx.request("GET", url, status_code=202)
    assert respx.stats.call_count == 0

    try:
        respx.start()
        response = await client.get(url)
        assert request.called is True
        assert response.status_code == 202
        assert response.text == ""
        assert respx.stats.call_count == 1

        respx.stop(reset=False)
        assert respx.stats.call_count == 1

        respx.stop()
        assert respx.stats.call_count == 0

    except Exception:  # pragma: nocover
        respx.stop()  # Cleanup global state on error, to not affect other tests
        raise


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "assert_all_called,do_post,raises",
    [
        (True, False, pytest.raises(AssertionError)),
        (True, True, does_not_raise()),
        (False, True, does_not_raise()),
        (False, False, does_not_raise()),
    ],
)
async def test_assert_all_called(client, assert_all_called, do_post, raises):
    with raises:
        async with respx.HTTPXMock(assert_all_called=assert_all_called) as httpx_mock:
            request1 = httpx_mock.get("https://foo.bar/1/", status_code=404)
            request2 = httpx_mock.post("https://foo.bar/", status_code=201)

            await client.get("https://foo.bar/1/")
            if do_post:
                await client.post("https://foo.bar/")

            assert request1.called is True
            assert request2.called is do_post


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "assert_all_mocked,raises",
    [(True, pytest.raises(AssertionError)), (False, does_not_raise())],
)
async def test_assert_all_mocked(client, assert_all_mocked, raises):
    with raises:
        async with respx.HTTPXMock(assert_all_mocked=assert_all_mocked) as httpx_mock:
            response = await client.get("https://foo.bar/")
            assert httpx_mock.stats.call_count == 1
            assert response.status_code == 200
    assert httpx_mock.stats.call_count == 0


@pytest.mark.asyncio
async def test_asgi():
    async with respx.mock:
        async with httpx.AsyncClient(app="fake-asgi") as client:
            url = "https://foo.bar/"
            content = lambda request: {"status": "ok"}
            headers = {"X-Foo": "bar"}
            request = respx.get(url, status_code=202, headers=headers, content=content)
            response = await client.get(url)
            assert request.called is True
            assert response.status_code == 202
            assert response.headers == httpx.Headers(
                {"Content-Type": "application/json", **headers}
            )
            assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_uds():
    async with respx.mock:
        async with httpx.AsyncClient(uds="/foo/bar.sock") as client:
            request = respx.get("https://foo.bar/", status_code=202)
            response = await client.get("https://foo.bar/")
            assert request.called is True
            assert response.status_code == 202
