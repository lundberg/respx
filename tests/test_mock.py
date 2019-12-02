import re
from contextlib import ExitStack as does_not_raise

import httpx
import pytest

import respx


@pytest.mark.asyncio
@respx.mock
async def test_decorating_test():
    assert respx.stats.call_count == 0
    request = respx.get("https://foo.bar/", status_code=202)
    response = await httpx.get("https://foo.bar/")
    assert request.called is True
    assert response.status_code == 202
    assert respx.stats.call_count == 1


@pytest.mark.asyncio
async def test_mock_fixture(httpx_mock):
    assert respx.stats.call_count == 0
    assert httpx_mock.stats.call_count == 0
    request = httpx_mock.get("https://foo.bar/", status_code=202)
    response = await httpx.get("https://foo.bar/")
    assert request.called is True
    assert response.status_code == 202
    assert respx.stats.call_count == 0
    assert httpx_mock.stats.call_count == 1


def test_global_sync_decorator(future):
    @respx.mock
    def test():
        assert respx.stats.call_count == 0
        request = respx.get("https://foo.bar/", status_code=202)
        response = future(httpx.get("https://foo.bar/"))
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_global_async_decorator(future):
    @respx.mock
    async def test():
        assert respx.stats.call_count == 0
        request = respx.get("https://foo.bar/", status_code=202)
        response = await httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    await test()
    assert respx.stats.call_count == 0


def test_local_sync_decorator(future):
    @respx.mock()
    def test(httpx_mock):
        assert respx.stats.call_count == 0
        request = httpx_mock.get("https://foo.bar/", status_code=202)
        response = future(httpx.get("https://foo.bar/"))
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_local_async_decorator():
    @respx.mock()
    async def test(httpx_mock):
        assert respx.stats.call_count == 0
        request = httpx_mock.get("https://foo.bar/", status_code=202)
        response = await httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    await test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_global_contextmanager():
    with respx.mock:
        assert respx.stats.call_count == 0
        request = respx.get("https://foo/bar/", status_code=202)
        response = await httpx.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    async with respx.mock:
        assert respx.stats.call_count == 0
        request = respx.get("https://foo/bar/", status_code=202)
        response = await httpx.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_local_contextmanager():
    with respx.mock() as httpx_mock:
        assert httpx_mock.stats.call_count == 0
        request = httpx_mock.get("https://foo/bar/", status_code=202)
        response = await httpx.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    async with respx.mock() as httpx_mock:
        assert httpx_mock.stats.call_count == 0
        request = httpx_mock.get("https://foo/bar/", status_code=202)
        response = await httpx.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert httpx_mock.stats.call_count == 1

    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_configured_decorator():
    @respx.mock(assert_all_called=False, assert_all_mocked=False)
    async def test(httpx_mock):
        assert httpx_mock.stats.call_count == 0
        request = httpx_mock.get("https://foo.bar/")
        response = await httpx.get("https://some.thing/")

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

        async with httpx.Client(base_url="https://foo.bar") as client:
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
async def test_start_stop():
    url = "https://foo.bar/"
    request = respx.request("GET", url, status_code=202)
    assert respx.stats.call_count == 0

    try:
        respx.start()
        response = await httpx.get(url)
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
async def test_assert_all_called(assert_all_called, do_post, raises):
    with raises:
        async with respx.HTTPXMock(assert_all_called=assert_all_called) as httpx_mock:
            request1 = httpx_mock.get("https://foo.bar/1/", status_code=404)
            request2 = httpx_mock.post("https://foo.bar/", status_code=201)

            await httpx.get("https://foo.bar/1/")
            if do_post:
                await httpx.post("https://foo.bar/")

            assert request1.called is True
            assert request2.called is do_post


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "assert_all_mocked,raises",
    [(True, pytest.raises(AssertionError)), (False, does_not_raise())],
)
async def test_assert_all_mocked(assert_all_mocked, raises):
    with raises:
        async with respx.HTTPXMock(assert_all_mocked=assert_all_mocked) as httpx_mock:
            response = await httpx.get("https://foo.bar/")
            assert httpx_mock.stats.call_count == 1
            assert response.status_code == 200
    assert httpx_mock.stats.call_count == 0
