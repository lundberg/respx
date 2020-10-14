import asyncio
import json as jsonlib
import os
import re
import socket
from unittest import mock

import httpx
import pytest

import respx
from respx import MockTransport
from respx.models import URL, RequestPattern, URLPattern


@pytest.mark.asyncio
async def test_http_methods(client):
    async with respx.mock:
        url = "https://foo.bar/"
        m = respx.get(url, status_code=404)
        respx.post(url, status_code=201)
        respx.put(url, status_code=202)
        respx.patch(url, status_code=500)
        respx.delete(url, status_code=204)
        respx.head(url, status_code=405)
        respx.options(url, status_code=501)

        response = httpx.get(url)
        assert response.status_code == 404
        response = await client.get(url)
        assert response.status_code == 404

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

        assert m.called is True
        assert respx.stats.call_count == 7 * 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,pattern",
    [
        ("https://foo.bar", "https://foo.bar"),
        ("https://foo.bar/", "https://foo.bar"),
        ("https://foo.bar", "https://foo.bar/"),
        ("https://foo.bar/?baz=1", "https://foo.bar"),
        ("https://foo.bar/?baz=1", "https://foo.bar/?baz=1"),
        ("https://foo.bar/?baz=1&qux=2", "https://foo.bar/?qux=2&baz=1"),
        ("https://foo.bar/baz/", None),
        ("https://foo.bar/baz/", ""),
        ("https://foo.bar/baz/", "https://foo.bar/baz/"),
        ("https://foo.bar/baz/", re.compile(r"^https://foo.bar/\w+/$")),
        ("https://foo.bar/baz/", (b"https", b"foo.bar", None, b"/baz/")),
        ("https://foo.bar:443/baz/", (b"https", b"foo.bar", 443, b"/baz/")),
    ],
)
async def test_url_match(client, url, pattern):
    async with MockTransport(assert_all_mocked=False) as respx_mock:
        request = respx_mock.get(pattern, content="baz")
        response = await client.get(url)
        assert request.called is True
        assert response.status_code == 200
        assert response.text == "baz"


@pytest.mark.asyncio
async def test_invalid_url_pattern():
    async with MockTransport() as respx_mock:
        with pytest.raises(ValueError):
            respx_mock.get(["invalid"])


@pytest.mark.asyncio
async def test_repeated_pattern(client):
    async with MockTransport() as respx_mock:
        url = "https://foo/bar/baz/"
        one = respx_mock.post(url, status_code=201)
        two = respx_mock.post(url, status_code=409)
        response1 = await client.post(url, json={})
        response2 = await client.post(url, json={})
        response3 = await client.post(url, json={})

        assert response1.status_code == 201
        assert response2.status_code == 409
        assert response3.status_code == 409
        assert respx_mock.stats.call_count == 3

        assert one.called is True
        assert one.call_count == 1
        statuses = [response.status_code for _, response in one.calls]
        assert statuses == [201]

        assert two.called is True
        assert two.call_count == 2
        statuses = [response.status_code for _, response in two.calls]
        assert statuses == [409, 409]


@pytest.mark.asyncio
async def test_status_code(client):
    async with MockTransport() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url, status_code=404)
        response = await client.get(url)

    assert request.called is True
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers,content_type,expected",
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
    async with MockTransport() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url, content_type=content_type, headers=headers)
        response = await client.get(url)
        assert request.called is True
        assert response.headers == httpx.Headers(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,expected",
    [
        (b"eldr\xc3\xa4v", "eldräv"),
        ("äpple", "äpple"),
        ("Geh&#xE4;usegröße", "Geh&#xE4;usegröße"),
    ],
)
async def test_text_encoding(client, content, expected):
    async with MockTransport() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.post(url, content=content)
        response = await client.post(url)
        assert request.called is True
        assert response.text == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,value,expected_content_type",
    [
        ("content", b"foobar", None),
        ("content", "foobar", "text/plain; charset=utf-8"),
        ("content", ["foo", "bar"], "application/json"),
        ("content", {"foo": "bar"}, "application/json"),
        ("text", "foobar", "text/plain; charset=utf-8"),
        ("html", "<strong>foobar</strong>", "text/html; charset=utf-8"),
        ("json", {"foo": "bar"}, "application/json"),
    ],
)
async def test_content_variants(client, key, value, expected_content_type):
    async with MockTransport() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url, **{key: value})

        async_response = await client.get(url)
        assert request.called is True
        assert async_response.headers.get("Content-Type") == expected_content_type
        assert async_response.content is not None

        respx_mock.reset()
        sync_response = httpx.get(url)
        assert request.called is True
        assert sync_response.headers.get("Content-Type") == expected_content_type
        assert sync_response.content is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,headers,expected_headers",
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
    async with MockTransport() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url, content=content, headers=headers)

        async_response = await client.get(url)
        assert request.called is True
        assert async_response.headers == httpx.Headers(expected_headers)
        assert async_response.json() == content

        respx_mock.reset()
        sync_response = httpx.get(url)
        assert request.called is True
        assert sync_response.headers == httpx.Headers(expected_headers)
        assert sync_response.json() == content


@pytest.mark.asyncio
async def test_raising_content(client):
    async with MockTransport() as respx_mock:
        url = "https://foo.bar/"
        request = respx_mock.get(url, content=httpx.ConnectTimeout("X-P", request=None))
        with pytest.raises(httpx.ConnectTimeout):
            await client.get(url)

        assert request.called is True
        _request, _response = request.calls[-1]
        assert _request is not None
        assert _response is None


@pytest.mark.asyncio
async def test_callable_content(client):
    async with MockTransport() as respx_mock:
        url_pattern = re.compile(r"https://foo.bar/(?P<slug>\w+)/")

        def content_callback(request, slug):
            request.read()  # TODO: Make this not needed, might affect pass-through
            content = jsonlib.loads(request.content)
            return f"hello {slug}{content['x']}"

        request = respx_mock.post(url_pattern, content=content_callback)

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


@pytest.mark.asyncio
async def test_request_callback(client):
    def callback(request, response):
        request.read()
        if request.url.host == "foo.bar" and request.content == b'{"foo": "bar"}':
            response.headers["X-Foo"] = "bar"
            response.content = lambda request, name: f"hello {name}"
            response.context["name"] = "lundberg"
            response.http_version = "HTTP/2"
            return response

    async with MockTransport(assert_all_called=False) as respx_mock:
        request = respx_mock.add(callback, status_code=202, headers={"X-Ham": "spam"})
        response = await client.post("https://foo.bar/", json={"foo": "bar"})

        assert request.called is True
        assert request.pass_through is None
        assert response.status_code == 202
        assert response.http_version == "HTTP/2"
        assert response.headers == httpx.Headers(
            {
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Length": "14",
                "X-Ham": "spam",
                "X-Foo": "bar",
            }
        )
        assert response.text == "hello lundberg"

        with pytest.raises(ValueError):
            respx_mock.add(lambda req, res: "invalid")
            await client.get("https://ham.spam/")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"method": "GET", "url": "https://example.org/", "pass_through": True}, True),
        ({"method": lambda request, response: request}, None),
        ({"method": RequestPattern("GET", "http://foo.bar/", pass_through=True)}, True),
    ],
)
async def test_pass_through(client, parameters, expected):
    async with MockTransport() as respx_mock:
        request = respx_mock.add(**parameters)

        with mock.patch(
            "asyncio.open_connection",
            side_effect=ConnectionRefusedError("test request blocked"),
        ) as open_connection:
            with pytest.raises(httpx.NetworkError):
                await client.get("https://example.org/")

        assert open_connection.called is True
        assert request.called is True
        assert request.pass_through is expected

    with MockTransport() as respx_mock:
        request = respx_mock.add(**parameters)

        with mock.patch(
            "socket.socket.connect", side_effect=socket.error("test request blocked")
        ) as connect:
            with pytest.raises(httpx.NetworkError):
                httpx.get("https://example.org/")

        assert connect.called is True
        assert request.called is True
        assert request.pass_through is expected


@pytest.mark.skipif(
    os.environ.get("PASS_THROUGH") is None, reason="External pass-through disabled"
)
@pytest.mark.asyncio
async def test_external_pass_through(client):  # pragma: nocover
    with respx.mock:
        # Mock pass-through call
        url = "https://httpbin.org/post"
        respx.get(url, content=b"", pass_through=True)

        # Mock a non-matching callback pattern pre-reading request data
        def callback(req, res):
            req.read()  # TODO: Make this not needed, might affect pass-through
            assert req.content == b'{"foo": "bar"}'
            return None

        respx.add(callback)

        # Make external pass-through call
        response = await client.post(url, json={"foo": "bar"})

        assert response.content is not None
        assert len(response.content) > 0
        assert "Content-Length" in response.headers
        assert int(response.headers["Content-Length"]) > 0
        assert response.json()["json"] == {"foo": "bar"}

        _, resp = respx.calls[-1]
        await resp.aread()  # Read async pass-through response
        assert resp.content == b"", "Should be 0, stream already read by real Response!"
        assert "Content-Length" in resp.headers
        assert int(resp.headers["Content-Length"]) > 0


@respx.mock
@pytest.mark.asyncio
async def test_parallel_requests(client):
    async def content(request, page):
        await asyncio.sleep(0.2 if page == "one" else 0.1)
        return page

    url_pattern = re.compile(r"https://foo/(?P<page>\w+)/$")
    respx.get(url_pattern, content=content)

    responses = await asyncio.gather(
        client.get("https://foo/one/"), client.get("https://foo/two/")
    )
    response_one, response_two = responses

    assert response_one.text == "one"
    assert response_two.text == "two"
    assert respx.stats.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method_str, client_method_attr",
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
async def test_add(client, method_str, client_method_attr):
    url = "https://example.org/"
    content = {"spam": "lots", "ham": "no, only spam"}
    async with MockTransport() as respx_mock:
        request = respx_mock.add(method_str, url, content=content)
        response = await getattr(client, client_method_attr)(url)
        assert request.called is True
        assert response.json() == content


@pytest.mark.parametrize(
    "url_parts, url_model, expected_matches",
    [
        ((b"http", b"foo.bar", None, b""), URLPattern("http://foo.bar"), True),
        ((b"http", b"foo.bar", 80, b"/"), URLPattern("http://foo.bar:80"), True),
        ((b"http", b"foo.bar", None, b"/"), URLPattern("http://foo.bar/"), True),
        ((b"http", b"foo.bar", None, b""), URLPattern("http://foo.bar/"), True),
        ((b"http", b"foo.bar", None, b"/baz"), URLPattern("http://foo.bar"), False),
        ((b"https", b"foo.bar", None, b""), URLPattern("http://foo.bar"), False),
        ((b"https", b"foo.bar", None, b""), URLPattern("https://foo.bar"), True),
        ((b"https", b"foo.bar", 443, b""), URLPattern("https://foo.bar:443"), True),
        ((b"http", b"foo.bar", None, b"?baz=1"), URLPattern("http://foo.bar"), True),
        (
            (b"http", b"foo.bar", None, b"?baz=1"),
            URLPattern("http://foo.bar/?baz=1"),
            True,
        ),
        (
            (b"http", b"foo.bar", None, b"/?baz=1"),
            URLPattern("http://foo.bar?baz=1"),
            True,
        ),
        (
            (b"http", b"foo.bar", None, b"?baz=1"),
            URLPattern("http://foo.bar?baz=2"),
            False,
        ),
        (
            (b"http", b"foo.bar", None, b"?baz=1"),
            URLPattern("http://foo.bar?baz=1&qux=2"),
            False,
        ),
        (
            (b"http", b"foo.bar", None, b"/path?qux=2&baz=1"),
            URLPattern("http://foo.bar/path?baz=1&qux=2"),
            True,
        ),
        (
            (b"http", b"foo.bar", None, b""),
            URLPattern(re.compile(r"http://foo\.bar")),
            True,
        ),
        (
            (b"http", b"foo.bar", None, b"?baz=1"),
            URLPattern(re.compile(r"http://foo\.bar"), params={"baz": 1}),
            True,
        ),
        (
            (b"http", b"foo.bar/qux", None, b"?baz=1"),
            URLPattern(re.compile(r"http://foo\.bar/qux"), params={"baz": 1}),
            True,
        ),
        (
            (b"http", b"foo.bar/qux", None, b"?baz=1"),
            URLPattern(re.compile(r"http://foo\.bar/qux"), params={"baz": 2}),
            False,
        ),
        (
            (b"http", b"foo.bar", None, b"?baz=1&qux=2"),
            URLPattern("http://foo.bar", params={"baz": 1, "qux": 2}),
            True,
        ),
        (
            (b"http", b"foo.bar", None, b"?baz=1&qux=2"),
            URLPattern("http://foo.bar", params={"baz": 1}),
            False,
        ),
        (
            (b"http", b"foo.bar", None, b""),
            URLPattern("http://foo.bar", params={}),
            True,
        ),
        (
            (b"http", b"foo.bar", None, b"?baz=1"),
            URLPattern("http://foo.bar", params={}),
            False,
        ),
    ],
)
def test_url_model_matches(
    url_parts: URL,
    url_model: URLPattern,
    expected_matches: bool,
) -> None:
    matches, _ = url_model.matches(url_parts)
    assert matches == expected_matches


@respx.mock
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,params,call_url",
    [
        ("https://foo/", "foo=bar&foo=foo", "https://foo/"),
        ("https://foo/", b"foo=bar&foo=foo", "https://foo/"),
        ("https://foo/", [("foo", "bar"), ("foo", "foo")], "https://foo/"),
        ("https://foo/", {"foo": "bar"}, "https://foo/"),
        (re.compile(r"https://foo/(?P<page>\w+)/"), {"foo": "bar"}, "https://foo/baz/"),
    ],
)
async def test_params(client, url, params, call_url):
    respx.get(url, params=params, content="spam spam")
    response = await client.get(call_url, params=params)
    assert response.text == "spam spam"


def test_pop():
    with respx.mock:
        respx.get("https://foo.bar/", alias="foobar")
        request_pattern = respx.pop("foobar")
        assert str(request_pattern.url._url) == "https://foo.bar/"


@respx.mock
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,params,call_url,call_params",
    [
        ("https://foo/", "foo=bar", "https://foo/", "foo=bar"),
        ("https://foo/", b"foo=bar", "https://foo/", b"foo=bar"),
        ("https://foo/", [("foo", "bar")], "https://foo/", [("foo", "bar")]),
        ("https://foo/", {"foo": "bar"}, "https://foo/", {"foo": "bar"}),
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
    respx.get(url, params=params, content="spam spam")
    response = await client.get(call_url, params=call_params)
    assert response.text == "spam spam"


@pytest.mark.asyncio
async def test_build_url_invalid_regex_params(client):
    with pytest.raises(ValueError):
        respx.get(re.compile(r"https://foo.bar/\?foo=bar"), params="baz=qux")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "base,url",
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
        respx_mock.get(url, content="spam spam")
        response = await client.get("https://foo.bar/baz/")
        assert response.text == "spam spam"
