from contextlib import ExitStack as does_not_raise

import httpx
import pytest

import respx
from respx.router import MockRouter
from respx.transports import MockTransport


@pytest.mark.asyncio
@respx.mock
async def test_decorating_test(client):
    assert respx.calls.call_count == 0
    respx.calls.assert_not_called()
    request = respx.route(url="https://foo.bar/", name="home").respond(202)
    response = await client.get("https://foo.bar/")
    assert request.called is True
    assert response.status_code == 202
    assert respx.calls.call_count == 1
    assert respx.routes["home"].call_count == 1
    respx.calls.assert_called_once()
    respx.routes["home"].calls.assert_called_once()


@pytest.mark.asyncio
async def test_mock_request_fixture(client, my_mock):
    assert respx.calls.call_count == 0
    assert my_mock.calls.call_count == 0
    response = await client.get("https://httpx.mock/")
    request = my_mock.routes["index"]
    assert request.called is True
    assert response.is_error
    assert response.status_code == 404
    assert respx.calls.call_count == 0
    assert my_mock.calls.call_count == 1


@pytest.mark.asyncio
async def test_mock_single_session_fixture(client, mocked_foo):
    current_foo_call_count = mocked_foo.calls.call_count
    response = await client.get("https://foo.api/api/bar/")
    request = mocked_foo.routes["bar"]
    assert request.called is True
    assert response.status_code == 200
    assert mocked_foo.calls.call_count == current_foo_call_count + 1


@pytest.mark.asyncio
async def test_mock_multiple_session_fixtures(client, mocked_foo, mocked_ham):
    current_foo_call_count = mocked_foo.calls.call_count
    current_ham_call_count = mocked_ham.calls.call_count

    response = await client.get("https://foo.api/api/")
    request = mocked_foo.routes["index"]
    assert request.called is True
    assert response.status_code == 202

    response = await client.get("https://ham.api/")
    request = mocked_foo.routes["index"]
    assert request.called is True
    assert response.status_code == 200

    assert mocked_foo.calls.call_count == current_foo_call_count + 1
    assert mocked_ham.calls.call_count == current_ham_call_count + 1


def test_global_sync_decorator():
    @respx.mock
    def test():
        assert respx.calls.call_count == 0
        request = respx.get("https://foo.bar/") % httpx.Response(202)
        response = httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 1

    assert respx.calls.call_count == 0
    test()
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
async def test_global_async_decorator(client):
    @respx.mock
    async def test():
        assert respx.calls.call_count == 0
        request = respx.get("https://foo.bar/") % httpx.Response(202)
        response = await client.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 1

    assert respx.calls.call_count == 0
    await test()
    assert respx.calls.call_count == 0


def test_local_sync_decorator():
    @respx.mock()
    def test(respx_mock):
        assert respx.calls.call_count == 0
        request = respx_mock.get("https://foo.bar/") % 202
        response = httpx.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 0
        assert respx_mock.calls.call_count == 1

    assert respx.calls.call_count == 0
    test()
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
async def test_local_async_decorator(client):
    @respx.mock()
    async def test(respx_mock):
        assert respx.calls.call_count == 0
        request = respx_mock.get("https://foo.bar/") % 202
        response = await client.get("https://foo.bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 0
        assert respx_mock.calls.call_count == 1

    await test()
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
async def test_global_contextmanager(client):
    with respx.mock:
        assert respx.calls.call_count == 0
        request = respx.get("https://foo/bar/") % 202
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 1

    async with respx.mock:
        assert respx.calls.call_count == 0
        request = respx.get("https://foo/bar/") % 202
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 1

    assert respx.calls.call_count == 0


@pytest.mark.asyncio
async def test_local_contextmanager(client):
    with respx.mock() as respx_mock:
        assert respx_mock.calls.call_count == 0
        request = respx_mock.get("https://foo/bar/") % 202
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 0
        assert respx_mock.calls.call_count == 1

    async with respx.mock() as respx_mock:
        assert respx_mock.calls.call_count == 0
        request = respx_mock.get("https://foo/bar/") % 202
        response = await client.get("https://foo/bar/")
        assert request.called is True
        assert response.status_code == 202
        assert respx.calls.call_count == 0
        assert respx_mock.calls.call_count == 1

    assert respx.calls.call_count == 0


@pytest.mark.asyncio
async def test_nested_local_contextmanager(client):
    with respx.mock() as respx_mock_1:
        get_request = respx_mock_1.get("https://foo/bar/") % 202

        with respx.mock() as respx_mock_2:
            post_request = respx_mock_2.post("https://foo/bar/") % 201
            assert len(respx_mock_1.routes) == 1
            assert len(respx_mock_2.routes) == 1

            response = await client.get("https://foo/bar/")
            assert get_request.called is True
            assert response.status_code == 202
            assert respx.calls.call_count == 0
            assert respx_mock_1.calls.call_count == 1
            assert respx_mock_2.calls.call_count == 0

            response = await client.post("https://foo/bar/")
            assert post_request.called is True
            assert response.status_code == 201
            assert respx.calls.call_count == 0
            assert respx_mock_1.calls.call_count == 1
            assert respx_mock_2.calls.call_count == 1

    assert len(respx.routes) == 0


@pytest.mark.asyncio
async def test_nested_global_contextmanager(client):
    with respx.mock:
        get_request = respx.get("https://foo/bar/") % 202
        assert len(respx.routes) == 1

        with respx.mock:
            post_request = respx.post("https://foo/bar/") % 201
            assert len(respx.routes) == 2

            response = await client.get("https://foo/bar/")
            assert get_request.called is True
            assert response.status_code == 202
            assert respx.calls.call_count == 1

            response = await client.post("https://foo/bar/")
            assert post_request.called is True
            assert response.status_code == 201
            assert respx.calls.call_count == 2

        assert len(respx.routes) == 1

    assert len(respx.routes) == 0


@pytest.mark.asyncio
async def test_configured_decorator(client):
    @respx.mock(assert_all_called=False, assert_all_mocked=False)
    async def test(respx_mock):
        assert respx_mock.calls.call_count == 0
        request = respx_mock.get("https://foo.bar/")
        response = await client.get("https://some.thing/")

        assert response.status_code == 200
        assert response.headers == httpx.Headers()
        assert response.text == ""

        assert request.called is False
        assert respx.calls.call_count == 0
        assert respx_mock.calls.call_count == 1

        _request, _response = respx_mock.calls.last
        assert _request is not None
        assert _response is not None
        assert respx_mock.calls.last.request is _request
        assert respx_mock.calls.last.response is _response
        assert _request.url == "https://some.thing/"

    await test()
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
async def test_configured_router_reuse(client):
    router = respx.mock()
    route = router.get("https://foo/bar/") % 404

    assert len(router.routes) == 1
    assert router.calls.call_count == 0

    with router:
        route.return_value = httpx.Response(202)
        response = await client.get("https://foo/bar/")
        assert route.called is True
        assert response.status_code == 202
        assert router.calls.call_count == 1
        assert respx.calls.call_count == 0

    assert len(router.routes) == 1
    assert route.called is False
    assert router.calls.call_count == 0

    async with router:
        assert router.calls.call_count == 0
        response = await client.get("https://foo/bar/")
        assert route.called is True
        assert response.status_code == 404
        assert router.calls.call_count == 1
        assert respx.calls.call_count == 0

    assert len(router.routes) == 1
    assert route.called is False
    assert router.calls.call_count == 0
    assert respx.calls.call_count == 0


@pytest.mark.asyncio
@respx.mock(base_url="https://ham.spam/")
async def test_nested_base_url(respx_mock=None):
    request = respx_mock.patch("/egg/") % dict(content="yolk")
    async with respx.mock(base_url="https://foo.bar/api/") as foobar_mock:
        request1 = foobar_mock.get("/baz/") % dict(content="baz")
        request2 = foobar_mock.post(path__regex=r"(?P<slug>\w+)/?$") % dict(text="slug")
        request3 = foobar_mock.route() % dict(content="ok")
        request4 = foobar_mock.head("http://localhost/apa/") % 204

        async with httpx.AsyncClient(base_url="https://foo.bar/api") as client:
            response = await client.get("/baz/")
            assert request1.called is True
            assert response.text == "baz"

            response = await client.post("/apa/")
            assert request2.called is True
            assert response.text == "slug"

            response = await client.put("/")
            assert request3.called is True
            assert response.text == "ok"

            response = await client.head("http://localhost/apa/")
            assert request4.called is True
            assert response.status_code == 204

            response = await client.patch("https://ham.spam/egg/")
            assert request.called is True
            assert response.text == "yolk"


def test_leakage(mocked_foo, mocked_ham):
    # NOTE: Including session fixtures, since they are pre-registered transports
    assert len(respx.routes) == 0
    assert len(respx.calls) == 0
    assert len(respx.mock.Mock.routers) == 2


@pytest.mark.asyncio
async def test_start_stop(client):
    url = "https://start.stop/"
    request = respx.get(url) % 202

    try:
        respx.start()
        response = await client.get(url)
        assert request.called is True
        assert response.status_code == 202
        assert response.text == ""
        assert respx.calls.call_count == 1

        respx.stop(clear=False, reset=False)
        assert len(respx.routes) == 1
        assert respx.calls.call_count == 1
        assert request.called is True

        respx.reset()
        assert len(respx.routes) == 1
        assert respx.calls.call_count == 0
        assert request.called is False

        respx.clear()
        assert len(respx.routes) == 0

    finally:  # pragma: nocover
        respx.stop()  # Cleanup global state on error, to not affect other tests


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
        async with MockRouter(assert_all_called=assert_all_called) as respx_mock:
            request1 = respx_mock.get("https://foo.bar/1/") % 404
            request2 = respx_mock.post("https://foo.bar/") % 201

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
        with MockRouter(assert_all_mocked=assert_all_mocked) as respx_mock:
            response = httpx.get("https://foo.bar/")
            assert respx_mock.calls.call_count == 1
            assert response.status_code == 200
    with raises:
        async with MockRouter(assert_all_mocked=assert_all_mocked) as respx_mock:
            response = await client.get("https://foo.bar/")
            assert respx_mock.calls.call_count == 1
            assert response.status_code == 200
    assert respx_mock.calls.call_count == 0


@pytest.mark.asyncio
async def test_asgi():
    async with respx.mock:
        async with httpx.AsyncClient(app="fake-asgi") as client:
            url = "https://foo.bar/"
            jzon = {"status": "ok"}
            headers = {"X-Foo": "bar"}
            request = respx.get(url) % dict(status_code=202, headers=headers, json=jzon)
            response = await client.get(url)
            assert request.called is True
            assert response.status_code == 202
            assert response.headers == httpx.Headers(
                {"Content-Type": "application/json", "Content-Length": "16", **headers}
            )
            assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_proxies():
    with respx.mock:
        respx.get("https://foo.bar/") % dict(json={"foo": "bar"})
        with httpx.Client(proxies={"https://": "https://1.1.1.1:1"}) as client:
            response = client.get("https://foo.bar/")
        assert response.json() == {"foo": "bar"}

    async with respx.mock:
        respx.get("https://foo.bar/") % dict(json={"foo": "bar"})
        async with httpx.AsyncClient(
            proxies={"https://": "https://1.1.1.1:1"}
        ) as client:
            response = await client.get("https://foo.bar/")
        assert response.json() == {"foo": "bar"}


@pytest.mark.xfail(strict=True)
@pytest.mark.asyncio
async def test_uds():  # pragma: no cover
    async with respx.mock:
        async with httpx.AsyncClient(uds="/foo/bar.sock") as client:
            request = respx.get("https://foo.bar/") % 202
            response = await client.get("https://foo.bar/")
            assert request.called is True
            assert response.status_code == 202


@pytest.mark.asyncio
async def test_mock_using_none():
    @respx.mock(using=None)
    async def test(respx_mock):
        respx_mock.get("https://example.org/") % 204
        transport = MockTransport(handler=respx_mock.handler)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("https://example.org/")
            assert response.status_code == 204

    await test()


@pytest.mark.asyncio
async def test_router_using_none():
    router = MockRouter(using=None)
    router.get("https://example.org/") % 204

    @router
    async def test():
        transport = MockTransport(handler=router.handler)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("https://example.org/")
            assert response.status_code == 204

    await test()
