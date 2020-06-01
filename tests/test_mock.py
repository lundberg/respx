import re
from contextlib import ExitStack as does_not_raise

import httpx
import pytest

import respx
from respx import MockTransport


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
async def test_mock_request_fixture(client, my_mock):
    assert respx.stats.call_count == 0
    assert my_mock.stats.call_count == 0
    response = await client.get("https://httpx.mock/")
    request = my_mock.aliases["index"]
    assert request.called is True
    assert response.is_error
    assert response.status_code == 404
    assert respx.stats.call_count == 0
    assert my_mock.stats.call_count == 1


@pytest.mark.asyncio
async def test_mock_single_session_fixture(client, mocked_foo):
    current_foo_call_count = mocked_foo.stats.call_count
    response = await client.get("https://foo.api/bar/")
    request = mocked_foo.aliases["bar"]
    assert request.called is True
    assert response.status_code == 200
    assert mocked_foo.stats.call_count == current_foo_call_count + 1


@pytest.mark.asyncio
async def test_mock_multiple_session_fixtures(client, mocked_foo, mocked_ham):
    current_foo_call_count = mocked_foo.stats.call_count
    current_ham_call_count = mocked_ham.stats.call_count

    response = await client.get("https://foo.api/")
    request = mocked_foo.aliases["index"]
    assert request.called is True
    assert response.status_code == 202

    response = await client.get("https://ham.api/")
    request = mocked_foo.aliases["index"]
    assert request.called is True
    assert response.status_code == 200

    assert mocked_foo.stats.call_count == current_foo_call_count + 1
    assert mocked_ham.stats.call_count == current_ham_call_count + 1


def test_global_sync_decorator():
    @respx.mock
    def test():
        assert respx.stats.call_count == 0
        request = respx.get("https://foo.bar/", status_code=202)
        response = httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    assert respx.stats.call_count == 0
    test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_global_async_decorator(client):
    @respx.mock
    async def test():
        assert respx.stats.call_count == 0
        request = respx.get("https://foo.bar/", status_code=202)
        response = await client.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 1

    assert respx.stats.call_count == 0
    await test()
    assert respx.stats.call_count == 0


def test_local_sync_decorator():
    @respx.mock()
    def test(respx_mock):
        assert respx.stats.call_count == 0
        request = respx_mock.get("https://foo.bar/", status_code=202)
        response = httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert respx_mock.stats.call_count == 1

    assert respx.stats.call_count == 0
    test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_local_async_decorator(client):
    @respx.mock()
    async def test(respx_mock):
        assert respx.stats.call_count == 0
        request = respx_mock.get("https://foo.bar/", status_code=202)
        response = await client.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert respx_mock.stats.call_count == 1

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
    with respx.mock() as respx_mock:
        assert respx_mock.stats.call_count == 0
        request = respx_mock.get("https://foo/bar/", status_code=202)
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert respx_mock.stats.call_count == 1

    async with respx.mock() as respx_mock:
        assert respx_mock.stats.call_count == 0
        request = respx_mock.get("https://foo/bar/", status_code=202)
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.stats.call_count == 0
        assert respx_mock.stats.call_count == 1

    assert respx.stats.call_count == 0


@pytest.mark.asyncio
async def test_nested_local_contextmanager(client):
    with respx.mock() as respx_mock_1:
        get_request = respx_mock_1.get("https://foo/bar/", status_code=202)

        with respx.mock() as respx_mock_2:
            post_request = respx_mock_2.post("https://foo/bar/", status_code=201)

            response = await client.get("https://foo/bar/")
            assert get_request.called is True
            assert response.status_code == 202
            assert respx.stats.call_count == 0
            assert respx_mock_1.stats.call_count == 1
            assert respx_mock_2.stats.call_count == 0

            response = await client.post("https://foo/bar/")
            assert post_request.called is True
            assert response.status_code == 201
            assert respx.stats.call_count == 0
            assert respx_mock_1.stats.call_count == 1
            assert respx_mock_2.stats.call_count == 1


@pytest.mark.asyncio
async def test_nested_global_contextmanager(client):
    with respx.mock:
        get_request = respx.get("https://foo/bar/", status_code=202)

        with respx.mock:
            post_request = respx.post("https://foo/bar/", status_code=201)

            response = await client.get("https://foo/bar/")
            assert get_request.called is True
            assert response.status_code == 202
            assert respx.stats.call_count == 1

            response = await client.post("https://foo/bar/")
            assert post_request.called is True
            assert response.status_code == 201
            assert respx.stats.call_count == 2


@pytest.mark.asyncio
async def test_configured_decorator(client):
    @respx.mock(assert_all_called=False, assert_all_mocked=False)
    async def test(respx_mock):
        assert respx_mock.stats.call_count == 0
        request = respx_mock.get("https://foo.bar/")
        response = await client.get("https://some.thing/")

        assert response.status_code == 200
        assert response.headers == httpx.Headers({"Content-Type": "text/plain"})
        assert response.text == ""

        assert request.called is False
        assert respx.stats.call_count == 0
        assert respx_mock.stats.call_count == 1

        _request, _response = respx_mock.calls[-1]
        assert _request is not None
        assert _response is not None
        assert _request.url == "https://some.thing/"

    await test()
    assert respx.stats.call_count == 0


@pytest.mark.asyncio
@respx.mock(base_url="https://ham.spam/")
async def test_base_url(respx_mock=None):
    request = respx_mock.patch("/egg/", content="yolk")
    async with respx.mock(base_url="https://foo.bar/") as foobar_mock:
        request1 = foobar_mock.get("/baz/", content="baz")
        request2 = foobar_mock.post(re.compile(r"(?P<slug>\w+)/?$"), content="slug")
        request3 = foobar_mock.put(content="ok")

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

            response = await client.patch("https://ham.spam/egg/")
            assert request.called is True
            assert response.text == "yolk"


@pytest.mark.asyncio
async def test_start_stop(client):
    url = "https://foo.bar/"
    request = respx.add("GET", url, status_code=202)
    assert respx.stats.call_count == 0

    try:
        respx.start()
        response = await client.get(url)
        assert request.called is True
        assert response.status_code == 202
        assert response.text == ""
        assert respx.stats.call_count == 1

        respx.stop(clear=False, reset=False)
        assert len(respx.mock.patterns) == 1
        assert respx.stats.call_count == 1
        assert request.called is True

        respx.reset()
        assert len(respx.mock.patterns) == 1
        assert respx.stats.call_count == 0
        assert request.called is False

        respx.clear()
        assert len(respx.mock.patterns) == 0

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
        async with MockTransport(assert_all_called=assert_all_called) as respx_mock:
            request1 = respx_mock.get("https://foo.bar/1/", status_code=404)
            request2 = respx_mock.post("https://foo.bar/", status_code=201)

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
        with MockTransport(assert_all_mocked=assert_all_mocked) as respx_mock:
            response = httpx.get("https://foo.bar/")
            assert respx_mock.stats.call_count == 1
            assert response.status_code == 200
    with raises:
        async with MockTransport(assert_all_mocked=assert_all_mocked) as respx_mock:
            response = await client.get("https://foo.bar/")
            assert respx_mock.stats.call_count == 1
            assert response.status_code == 200
    assert respx_mock.stats.call_count == 0


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
async def test_proxies():
    with respx.mock:
        respx.get("https://foo.bar/", content={"foo": "bar"})
        with httpx.Client(proxies={"https": "https://1.1.1.1:1"}) as client:
            response = client.get("https://foo.bar/")
        assert response.json() == {"foo": "bar"}

    async with respx.mock:
        respx.get("https://foo.bar/", content={"foo": "bar"})
        async with httpx.AsyncClient(proxies={"https": "https://1.1.1.1:1"}) as client:
            response = await client.get("https://foo.bar/")
        assert response.json() == {"foo": "bar"}


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_deprecated():
    url = "https://foo.bar/"
    with respx.mock:
        respx.request("POST", url, status_code=201)
        with respx.HTTPXMock() as httpx_mock:
            httpx_mock.request("GET", url)
            response = httpx.post(url)
            assert response.status_code == 201
            response = httpx.get(url)
            assert response.status_code == 200


@pytest.mark.xfail(strict=True)
@pytest.mark.asyncio
async def test_uds():  # pragma: no cover
    async with respx.mock:
        async with httpx.AsyncClient(uds="/foo/bar.sock") as client:
            request = respx.get("https://foo.bar/", status_code=202)
            response = await client.get("https://foo.bar/")
            assert request.called is True
            assert response.status_code == 202
