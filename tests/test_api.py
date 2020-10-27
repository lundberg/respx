import asyncio
import json as jsonlib
import os
import re
import socket
import warnings
from unittest import mock

import httpcore
import httpx
import pytest

import respx
from respx import MockTransport
from respx.models import MockResponse, RequestPattern, ResponseTemplate, Route


@pytest.mark.asyncio
async def test_http_methods(client):
    async with respx.mock:
        url = "https://foo.bar/"
        route = respx.get(url) % 404
        respx.post(url).respond(201)
        respx.put(url).respond(202)
        respx.patch(url).respond(500)
        respx.delete(url).respond(204)
        respx.head(url).respond(405)
        respx.options(url).respond(status_code=501)

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

        assert route.called is True
        assert respx.calls.call_count == 7 * 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,pattern",
    [
        ("https://foo.bar", "https://foo.bar"),
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

        assert one is two
        assert len(one._responses) == 2

        response1 = await client.post(url, json={})
        response2 = await client.post(url, json={})
        response3 = await client.post(url, json={})

        assert response1.status_code == 201
        assert response2.status_code == 409
        assert response3.status_code == 409
        assert respx_mock.calls.call_count == 3

        assert one.called is True
        assert one.call_count == 3
        statuses = [call.response.status_code for call in one.calls]
        assert statuses == [201, 409, 409]


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

        # Test httpx exception class get instantiated
        route = respx_mock.get(url).side_effect(httpx.ConnectError)
        with pytest.raises(httpx.ConnectError):
            await client.get(url)

        assert route.called is True
        assert route.calls.last.request is not None
        assert route.calls.last.response is None


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
            response.status_code = 202
            response.headers["X-Foo"] = "bar"
            response.content = lambda request, name: f"hello {name}"
            response.context["name"] = "lundberg"
            response.http_version = "HTTP/2"
            return response

    async with MockTransport(assert_all_called=False) as respx_mock:
        request = respx_mock.add(callback)
        _request = respx_mock.add(callback)
        assert request is _request

        response = await client.post("https://foo.bar/", json={"foo": "bar"})
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

        with pytest.raises(ValueError):
            respx_mock.get("https://ham.spam/").side_effect(lambda req, res: "invalid")
            await client.get("https://ham.spam/")

        with pytest.raises(httpx.NetworkError):

            def _callback(request):
                raise httpcore.NetworkError()

            respx_mock.get("https://egg.plant").side_effect(_callback)
            await client.get("https://egg.plant/")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args,kwargs,expected",
    [
        (
            [],
            {"method": "GET", "url": "https://example.org/", "pass_through": True},
            True,
        ),
        ([lambda request, response: request], {}, False),
        ([lambda request: request], {}, False),
        ([Route().pass_through()], {}, True),
    ],
)
async def test_pass_through(client, args, kwargs, expected):
    async with MockTransport() as respx_mock:
        request = respx_mock.add(*args, **kwargs)

        with mock.patch(
            "asyncio.open_connection",
            side_effect=ConnectionRefusedError("test request blocked"),
        ) as open_connection:
            with pytest.raises(httpx.NetworkError):
                await client.get("https://example.org/")

        assert open_connection.called is True
        assert request.called is True
        assert request.is_pass_through is expected

    with MockTransport() as respx_mock:
        request = respx_mock.add(*args, **kwargs)

        with mock.patch(
            "socket.socket.connect", side_effect=socket.error("test request blocked")
        ) as connect:
            with pytest.raises(httpx.NetworkError):
                httpx.get("https://example.org/")

        assert connect.called is True
        assert request.called is True
        assert request.is_pass_through is expected


@pytest.mark.skipif(
    os.environ.get("PASS_THROUGH") is None, reason="External pass-through disabled"
)
@pytest.mark.asyncio
async def test_external_pass_through(client):  # pragma: nocover
    with respx.mock:
        # Mock pass-through call
        url = "https://httpbin.org/post"
        route = respx.post(url).respond(content=b"").pass_through()

        # Mock a non-matching callback pattern pre-reading request data
        def callback(req, res):
            req.read()  # TODO: Make this not needed, might affect pass-through
            assert req.content == b'{"foo": "bar"}'
            return None

        respx.add(callback)

        # Make external pass-through call
        assert route.call_count == 0
        response = await client.post(url, json={"foo": "bar"})

        assert response.content is not None
        assert len(response.content) > 0
        assert "Content-Length" in response.headers
        assert int(response.headers["Content-Length"]) > 0
        assert response.json()["json"] == {"foo": "bar"}

        resp = respx.calls.last.response
        await resp.aread()  # Read async pass-through response
        assert resp.content == b"", "Should be 0, stream already read by real Response!"
        assert "Content-Length" in resp.headers
        assert int(resp.headers["Content-Length"]) > 0

        # TODO: Routed and recorded twice; AsyncConnectionPool + AsyncHTTPConnection
        assert route.call_count == 2
        assert respx.calls.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_parallel_requests(client):
    def content(request, page):
        return page

    url_pattern = re.compile(r"https://foo/(?P<page>\w+)/$")
    respx.get(url_pattern, content=content)

    responses = await asyncio.gather(
        client.get("https://foo/one/"), client.get("https://foo/two/")
    )
    response_one, response_two = responses

    assert response_one.text == "one"
    assert response_two.text == "two"
    assert respx.calls.call_count == 2


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


def test_pop():
    with respx.mock:
        request = respx.get("https://foo.bar/", name="foobar")
        popped = respx.pop("foobar")
        assert popped is request


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


@pytest.mark.asyncio
async def test_deprecated_apis():
    with respx.mock:
        url = "https://foo.bar/"

        # Response kwargs among request kwargs
        with warnings.catch_warnings(record=True) as w:
            respx.get(url, status_code=201)
            respx.get(url, headers={})
            respx.get(url, content_type="foo/bar")
            respx.get(url, content="")
            respx.get(url, text="")
            respx.get(url, html="")
            respx.get(url, json={})
            respx.get(url, pass_through=True)
            assert len(w) == 8

        # Add route by http method string
        with warnings.catch_warnings(record=True) as w:
            respx.add("GET", url)
            assert len(w) == 1

        # Alias and aliases
        with warnings.catch_warnings(record=True) as w:
            request_pattern = respx.get(url, alias="index")
            name = request_pattern.alias
            aliased_pattern = respx.mock.aliases["index"]
            assert aliased_pattern is request_pattern
            assert name == request_pattern.name
            assert len(w) == 3

        # RequestPattern
        with warnings.catch_warnings(record=True) as w:
            callback = lambda req, res: res  # pragma: nocover
            request_pattern = RequestPattern(callback)
            assert request_pattern.has_side_effect

            request_pattern = RequestPattern(
                "GET", "https://foo.bar/", pass_through=True
            )
            assert request_pattern.is_pass_through
            assert len(w) == 2

        # ResponseTemplate
        with warnings.catch_warnings(record=True) as w:
            request = httpx.Request("GET", "https://foo.bar/")

            callback = lambda request: ResponseTemplate(201)
            request_pattern = RequestPattern(callback, response=ResponseTemplate(444))
            assert request_pattern.resolve(request).status_code == 201

            request_pattern = RequestPattern("GET", response=ResponseTemplate(444))
            assert request_pattern.resolve(request).status_code == 444

            assert len(w) == 5

        # Mixing callback and response details
        with pytest.raises(NotImplementedError):
            callback = lambda request: ResponseTemplate(201)  # pragma: nocover
            respx.Router().add(callback, status_code=201)

        # Async callback
        with pytest.raises(NotImplementedError):

            async def callback(request):
                return None  # pragma: nocover

            mock_response = MockResponse(content=callback)
            request = httpx.Request("GET", "http://foo.bar/")
            mock_response.as_response(request)
