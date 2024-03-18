import asyncio
import json as jsonlib
import re
import socket
from unittest import mock

import httpcore
import httpx
import pytest

import respx
from respx.models import Route
from respx.patterns import M
from respx.router import MockRouter


async def test_http_methods(client):
    async with respx.mock:
        url = "https://foo.bar"
        route = respx.get(url, path="/") % 404
        respx.post(url, path="/").respond(200)
        respx.post(url, path="/").respond(201)
        respx.put(url, path="/").respond(202)
        respx.patch(url, path="/").respond(500)
        respx.delete(url, path="/").respond(204)
        respx.head(url, path="/").respond(405)
        respx.options(url, path="/").respond(status_code=501)
        respx.request("GET", url, path="/baz/").respond(status_code=204)
        url += "/"

        response = httpx.get(url)
        assert response.status_code == 404
        response = await client.get(url)
        assert response.status_code == 404

        response = httpx.get(url + "baz/")
        assert response.status_code == 204
        response = await client.get(url + "baz/")
        assert response.status_code == 204

        response = httpx.post(url)
        assert response.status_code == 201
        response = await client.post(url)
        assert response.status_code == 201

        response = httpx.put(url)
        assert response.status_code == 202
        response = await client.put(url)
        assert response.status_code == 202

        response = httpx.patch(url)
        assert response.status_code == 500
        response = await client.patch(url)
        assert response.status_code == 500

        response = httpx.delete(url)
        assert response.status_code == 204
        response = await client.delete(url)
        assert response.status_code == 204

        response = httpx.head(url)
        assert response.status_code == 405
        response = await client.head(url)
        assert response.status_code == 405

        response = httpx.options(url)
        assert response.status_code == 501
        response = await client.options(url)
        assert response.status_code == 501

        assert route.called is True
        assert respx.calls.call_count == 8 * 2


@pytest.mark.parametrize(
    ("url", "pattern"),
    [
        ("https://foo.bar", "https://foo.bar"),
        ("https://foo.bar/baz/", None),
        ("https://foo.bar/baz/", ""),
        ("https://foo.bar/baz/", "https://foo.bar/baz/"),
        ("https://foo.bar/baz/", re.compile(r"^https://foo.bar/\w+/$")),
        ("https://foo.bar/baz/", (b"https", b"foo.bar", None, b"/baz/")),
        ("https://foo.bar:443/baz/", (b"https", b"foo.bar", 443, b"/baz/")),
        ("https://foo.bar/%08", "https://foo.bar/%08"),
    ],
)
async def test_url_match(client, url, pattern):
    async with MockRouter(assert_all_mocked=False) as respx_mock:
        request = respx_mock.get(pattern) % dict(content="baz")
        response = await client.get(url)
        assert request.called is True
        assert response.status_code == 200
        assert response.text == "baz"


async def test_invalid_url_pattern():
    async with MockRouter() as respx_mock:
        with pytest.raises(TypeError):
            respx_mock.get(["invalid"])  # type: ignore[arg-type]


async def test_repeated_pattern(client):
    async with MockRouter() as respx_mock:
        url = "https://foo/bar/baz/"
        route = respx_mock.post(url)
        route.side_effect = [
            httpx.Response(201),
            httpx.Response(409),
        ]

        response1 = await client.post(url, json={})
        response2 = await client.post(url, json={})
        with pytest.raises(RuntimeError):
            await client.post(url, json={})

        assert response1.status_code == 201
        assert response2.status_code == 409
        assert respx_mock.calls.call_count == 2

        assert route.called is True
        assert route.call_count == 2
        statuses = [call.response.status_code for call in route.calls]
        assert statuses == [201, 409]


async def test_status_code(client):
    async with MockRouter() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url) % 404
        response = await client.get(url)

    assert request.called is True
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("headers", "content_type", "expected"),
    [
        ({"X-Foo": "bar"}, None, {"X-Foo": "bar"}),
        (
            {"Content-Type": "foo/bar", "X-Foo": "bar"},
            None,
            {"Content-Type": "foo/bar", "X-Foo": "bar"},
        ),
        (
            {"Content-Type": "foo/bar", "X-Foo": "bar"},
            "ham/spam",
            {"Content-Type": "ham/spam", "X-Foo": "bar"},
        ),
    ],
)
async def test_headers(client, headers, content_type, expected):
    async with MockRouter() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url).respond(
            headers=headers, content_type=content_type
        )
        response = await client.get(url)
        assert request.called is True
        assert response.headers == httpx.Headers(expected)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"eldr\xc3\xa4v", "eldräv"),
        ("äpple", "äpple"),
        ("Geh&#xE4;usegröße", "Geh&#xE4;usegröße"),
    ],
)
async def test_text_encoding(client, content, expected):
    async with MockRouter() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.post(url) % dict(content=content)
        response = await client.post(url)
        assert request.called is True
        assert response.text == expected


@pytest.mark.parametrize(
    ("key", "value", "expected_content_type"),
    [
        ("content", b"foobar", None),
        ("content", "foobar", None),
        ("json", ["foo", "bar"], "application/json"),
        ("json", {"foo": "bar"}, "application/json"),
        ("text", "foobar", "text/plain; charset=utf-8"),
        ("html", "<strong>foobar</strong>", "text/html; charset=utf-8"),
    ],
)
async def test_content_variants(client, key, value, expected_content_type):
    async with MockRouter() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url) % {key: value}

        async_response = await client.get(url)
        assert request.called is True
        assert async_response.headers.get("Content-Type") == expected_content_type
        assert async_response.content is not None

        respx_mock.reset()
        sync_response = httpx.get(url)
        assert request.called is True
        assert sync_response.headers.get("Content-Type") == expected_content_type
        assert sync_response.content is not None


@pytest.mark.parametrize(
    ("content", "headers", "expected_headers"),
    [
        (
            {"foo": "bar"},
            {"X-Foo": "bar"},
            {
                "Content-Type": "application/json",
                "Content-Length": "14",
                "X-Foo": "bar",
            },
        ),
        (
            ["foo", "bar"],
            {"Content-Type": "application/json; charset=utf-8", "X-Foo": "bar"},
            {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": "14",
                "X-Foo": "bar",
            },
        ),
    ],
)
async def test_json_content(client, content, headers, expected_headers):
    async with MockRouter() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url) % dict(json=content, headers=headers)

        async_response = await client.get(url)
        assert request.called is True
        assert async_response.headers == httpx.Headers(expected_headers)
        assert async_response.json() == content

        respx_mock.reset()
        sync_response = httpx.get(url)
        assert request.called is True
        assert sync_response.headers == httpx.Headers(expected_headers)
        assert sync_response.json() == content


def test_json_post_body():
    post_url = "https://example.org/"
    get_url = "https://something.else/"

    with respx.mock:
        post_route = respx.post(post_url, json={"foo": "bar"}) % 201
        get_route = respx.get(get_url) % 204

        post_response = httpx.post(post_url, json={"foo": "bar"})
        assert post_response.status_code == 201
        assert post_route.called

        get_response = httpx.get(get_url)
        assert get_response.status_code == 204
        assert get_route.called


def test_data_post_body():
    with respx.mock:
        url = "https://foo.bar/"
        route = respx.post(url, data={"foo": "bar"}) % 201
        response = httpx.post(url, data={"foo": "bar"}, files={"file": b"..."})
        assert response.status_code == 201
        assert route.called


async def test_raising_content(client):
    async with MockRouter() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url)
        request.side_effect = httpx.ConnectTimeout("X-P", request=None)
        with pytest.raises(httpx.ConnectTimeout):
            await client.get(url)

        assert request.called is True
        _request, _response = request.calls[-1]
        assert _request is not None
        assert _response is None

        # Test httpx exception class get instantiated
        route = respx_mock.get(url).mock(side_effect=httpx.ConnectError)
        with pytest.raises(httpx.ConnectError):
            await client.get(url)

        assert route.call_count == 2
        assert route.calls.last.request is not None
        assert route.calls.last.has_response is False
        with pytest.raises(ValueError, match="has no response"):
            assert route.calls.last.response


async def test_callable_content(client):
    async with MockRouter() as respx_mock:
        url_pattern = re.compile(r"https://foo.bar/(?P<slug>\w+)/")

        def content_callback(request, slug):
            content = jsonlib.loads(request.content)
            return respx.MockResponse(content=f"hello {slug}{content['x']}")

        request = respx_mock.post(url_pattern)
        request.side_effect = content_callback

        async_response = await client.post("https://foo.bar/world/", json={"x": "."})
        assert request.called is True
        assert async_response.status_code == 200
        assert async_response.text == "hello world."
        assert request.calls[-1][0].content == b'{"x": "."}'

        respx_mock.reset()
        sync_response = httpx.post("https://foo.bar/jonas/", json={"x": "!"})
        assert request.called is True
        assert sync_response.status_code == 200
        assert sync_response.text == "hello jonas!"
        assert request.calls[-1][0].content == b'{"x": "!"}'


async def test_request_callback(client):
    def callback(request, name):
        if request.url.host == "foo.bar" and request.content == b'{"foo": "bar"}':
            return respx.MockResponse(
                202,
                headers={"X-Foo": "bar"},
                text=f"hello {name}",
                http_version="HTTP/2",
            )
        return httpx.Response(404)

    async with MockRouter(assert_all_called=False) as respx_mock:
        request = respx_mock.post(host="foo.bar", path__regex=r"/(?P<name>\w+)/")
        request.side_effect = callback

        response = await client.post("https://foo.bar/lundberg/")
        assert response.status_code == 404

        response = await client.post("https://foo.bar/lundberg/", json={"foo": "bar"})
        assert request.called is True
        assert not request.is_pass_through
        assert response.status_code == 202
        assert response.http_version == "HTTP/2"
        assert response.headers == httpx.Headers(
            {
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Length": "14",
                "X-Foo": "bar",
            }
        )
        assert response.text == "hello lundberg"

        respx_mock.get("https://ham.spam/").mock(
            side_effect=lambda req: "invalid"  # type: ignore[arg-type]
        )

        def _callback(request):
            raise httpcore.NetworkError()

        respx_mock.get("https://egg.plant").mock(side_effect=_callback)

        with pytest.raises(TypeError):
            await client.get("https://ham.spam/")

        with pytest.raises(httpx.NetworkError):
            await client.get("https://egg.plant/")


@pytest.mark.parametrize(
    ("using", "route", "expected"),
    [
        ("httpcore", Route(url="https://example.org/").pass_through(), True),
        ("httpx", Route(url="https://example.org/").pass_through(), True),
        ("httpcore", Route().mock(side_effect=lambda request: request), False),
        ("httpcore", Route().pass_through(), True),
    ],
)
async def test_pass_through(client, using, route, expected):
    async with MockRouter(using=using) as respx_mock:
        request = respx_mock.add(route)

        with mock.patch(
            "anyio.connect_tcp",
            side_effect=ConnectionRefusedError("test request blocked"),
        ) as open_connection:
            with pytest.raises(httpx.NetworkError):
                await client.get("https://example.org/")

        assert open_connection.called is True
        assert request.called is True
        assert request.is_pass_through is expected

    with MockRouter(using=using) as respx_mock:
        request = respx_mock.add(route)

        with mock.patch(
            "socket.create_connection", side_effect=socket.error("test request blocked")
        ) as connect:
            with pytest.raises(httpx.NetworkError):
                httpx.get("https://example.org/")

        assert connect.called is True
        assert request.called is True
        assert request.is_pass_through is expected


@respx.mock
async def test_parallel_requests(client):
    def content(request, page):
        return httpx.Response(200, text=page)

    url_pattern = re.compile(r"https://foo/(?P<page>\w+)/$")
    respx.get(url_pattern).mock(side_effect=content)

    responses = await asyncio.gather(
        client.get("https://foo/one/"), client.get("https://foo/two/")
    )
    response_one, response_two = responses

    assert response_one.text == "one"
    assert response_two.text == "two"
    assert respx.calls.call_count == 2


@pytest.mark.parametrize(
    ("method_str", "client_method_attr"),
    [
        ("DELETE", "delete"),
        ("delete", "delete"),
        ("GET", "get"),
        ("get", "get"),
        ("HEAD", "head"),
        ("head", "head"),
        ("OPTIONS", "options"),
        ("options", "options"),
        ("PATCH", "patch"),
        ("patch", "patch"),
        ("POST", "post"),
        ("post", "post"),
        ("PUT", "put"),
        ("put", "put"),
    ],
)
async def test_method_case(client, method_str, client_method_attr):
    url = "https://example.org/"
    content = {"spam": "lots", "ham": "no, only spam"}
    async with MockRouter() as respx_mock:
        request = respx_mock.route(method=method_str, url=url) % dict(json=content)
        response = await getattr(client, client_method_attr)(url)
        assert request.called is True
        assert response.json() == content


def test_pop():
    with respx.mock:
        request = respx.get("https://foo.bar/", name="foobar")
        popped = respx.pop("foobar")
        assert popped is request

        with pytest.raises(KeyError):
            respx.pop("foobar")

        assert respx.pop("foobar", "custom default") == "custom default"


@respx.mock
@pytest.mark.parametrize(
    ("url", "params", "call_url", "call_params"),
    [
        ("https://foo/", "foo=bar", "https://foo/", "foo=bar"),
        ("https://foo/", b"foo=bar", "https://foo/", b"foo=bar"),
        ("https://foo/", [("foo", "bar")], "https://foo/", [("foo", "bar")]),
        ("https://foo/", {"foo": "bar"}, "https://foo/", {"foo": "bar"}),
        ("https://foo/", (("foo", "bar"),), "https://foo/", (("foo", "bar"),)),
        ("https://foo?foo=bar", "baz=qux", "https://foo?foo=bar", "baz=qux"),
        ("https://foo?foo=bar", "baz=qux", "https://foo?foo=bar&baz=qux", None),
        (re.compile(r"https://foo/(\w+)/"), "foo=bar", "https://foo/bar/", "foo=bar"),
        (httpx.URL("https://foo/"), "foo=bar", "https://foo/", "foo=bar"),
        (
            httpx.URL("https://foo?foo=bar"),
            "baz=qux",
            "https://foo?foo=bar&baz=qux",
            None,
        ),
    ],
)
async def test_params_match(client, url, params, call_url, call_params):
    respx.get(url, params=params) % dict(content="spam spam")
    response = await client.get(call_url, params=call_params)
    assert response.text == "spam spam"


@pytest.mark.parametrize(
    ("base", "url"),
    [
        (None, "https://foo.bar/baz/"),
        ("", "https://foo.bar/baz/"),
        ("https://foo.bar", "baz/"),
        ("https://foo.bar/", "baz/"),
        ("https://foo.bar/", "/baz/"),
        ("https://foo.bar/baz/", None),
        ("https://foo.bar/", re.compile(r"/(\w+)/")),
    ],
)
async def test_build_url_base(client, base, url):
    with respx.mock(base_url=base) as respx_mock:
        respx_mock.get(url) % dict(content="spam spam")
        response = await client.get("https://foo.bar/baz/")
        assert response.text == "spam spam"


def test_add():
    with respx.mock:
        route = Route(method="GET", url="https://foo.bar/")
        respx.add(route, name="foobar")

        response = httpx.get("https://foo.bar/")
        assert response.status_code == 200
        assert respx.routes["foobar"].called

        with pytest.raises(TypeError):
            respx.add(route, status_code=418)  # type: ignore[call-arg]

        with pytest.raises(ValueError, match="Invalid route"):
            respx.add("GET")  # type: ignore[arg-type]

        with pytest.raises(NotImplementedError):
            route.name = "spam"

        with pytest.raises(NotImplementedError):
            route.pattern &= M(params={"foo": "bar"})


def test_respond():
    with respx.mock:
        route = respx.get("https://foo.bar/").respond(
            content="<apa>lundberg</apa>",
            content_type="text/xml",
            http_version="HTTP/2",
        )
        response = httpx.get("https://foo.bar/")
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "text/xml"
        assert response.http_version == "HTTP/2"

        with pytest.raises(TypeError, match="content can only be"):
            route.respond(content={})

        with pytest.raises(TypeError, match="content can only be"):
            route.respond(content=Exception())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"content": b"foobar"},
        {"content": "foobar"},
        {"json": {"foo": "bar"}},
        {"json": [{"foo": "bar", "ham": "spam"}, {"zoo": "apa", "egg": "yolk"}]},
        {"data": {"animal": "Räv", "name": "Röda Räven"}},
    ],
)
async def test_async_post_content(kwargs):
    async with respx.mock:
        respx.post("https://foo.bar/", **kwargs) % 201
        async with httpx.AsyncClient() as client:
            response = await client.post("https://foo.bar/", **kwargs)
            assert response.status_code == 201
