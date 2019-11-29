import asyncio
import re

import asynctest
import httpx
import pytest

import respx


@pytest.mark.asyncio
async def test_http_methods():
    async with respx.HTTPXMock() as httpx_mock:
        url = "https://foo.bar/"
        m = httpx_mock.get(url, status_code=404)
        httpx_mock.post(url, status_code=201)
        httpx_mock.put(url, status_code=202)
        httpx_mock.patch(url, status_code=500)
        httpx_mock.delete(url, status_code=204)
        httpx_mock.head(url, status_code=405)
        httpx_mock.options(url, status_code=501)

        response = await httpx.get(url)
        assert response.status_code == 404
        response = await httpx.post(url)
        assert response.status_code == 201
        response = await httpx.put(url)
        assert response.status_code == 202
        response = await httpx.patch(url)
        assert response.status_code == 500
        response = await httpx.delete(url)
        assert response.status_code == 204
        response = await httpx.head(url)
        assert response.status_code == 405
        response = await httpx.options(url)
        assert response.status_code == 501

        assert m.called is True
        assert httpx_mock.stats.call_count == 7


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url", ["https://foo.bar/baz/", re.compile(r"^https://foo.bar/\w+/$")]
)
async def test_url_match(url):
    async with respx.HTTPXMock(assert_all_mocked=False) as httpx_mock:
        request = httpx_mock.get(url, content="baz")
        response = await httpx.get("https://foo.bar/baz/")
        assert request.called is True
        assert response.status_code == 200
        assert response.text == "baz"


@pytest.mark.asyncio
async def test_invalid_url_pattern():
    async with respx.HTTPXMock(assert_all_called=False) as httpx_mock:
        request = httpx_mock.get(["invalid"])
        with pytest.raises(ValueError):
            await httpx.get("https://foo.bar/")
        assert request.called is False


@pytest.mark.asyncio
async def test_repeated_pattern():
    async with respx.HTTPXMock() as httpx_mock:
        url = "https://foo/bar/baz/"
        one = httpx_mock.post(url, status_code=201)
        two = httpx_mock.post(url, status_code=409)
        response1 = await httpx.post(url, json={})
        response2 = await httpx.post(url, json={})
        response3 = await httpx.post(url, json={})

        assert response1.status_code == 201
        assert response2.status_code == 409
        assert response3.status_code == 409
        assert httpx_mock.stats.call_count == 3

        assert one.called is True
        assert one.call_count == 1
        statuses = [response.status_code for _, response in one.calls]
        assert statuses == [201]

        assert two.called is True
        assert two.call_count == 2
        statuses = [response.status_code for _, response in two.calls]
        assert statuses == [409, 409]


@pytest.mark.asyncio
async def test_status_code():
    async with respx.HTTPXMock() as httpx_mock:
        url = "https://foo.bar/"
        request = httpx_mock.get(url, status_code=404)
        response = await httpx.get(url)

    assert request.called is True
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers,content_type,expected",
    [
        ({"X-Foo": "bar"}, None, {"Content-Type": "text/plain", "X-Foo": "bar"}),
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
async def test_headers(headers, content_type, expected):
    async with respx.HTTPXMock() as httpx_mock:
        url = "https://foo.bar/"
        request = httpx_mock.get(url, content_type=content_type, headers=headers)
        response = await httpx.get(url)
        assert request.called is True
        assert response.headers == httpx.Headers(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,expected", [(b"eldr\xc3\xa4v", "eldräv"), ("äpple", "äpple")]
)
async def test_text_content(content, expected):
    async with respx.HTTPXMock() as httpx_mock:
        url = "https://foo.bar/"
        content_type = "text/plain; charset=utf-8"  # TODO: Remove once respected
        request = httpx_mock.post(url, content=content, content_type=content_type)
        response = await httpx.post(url)
        assert request.called is True
        assert response.text == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,headers,expected_headers",
    [
        (
            {"foo": "bar"},
            {"X-Foo": "bar"},
            {"Content-Type": "application/json", "X-Foo": "bar"},
        ),
        (
            ["foo", "bar"],
            {"Content-Type": "application/json; charset=utf-8", "X-Foo": "bar"},
            None,
        ),
    ],
)
async def test_json_content(content, headers, expected_headers):
    async with respx.HTTPXMock() as httpx_mock:
        url = "https://foo.bar/"
        request = httpx_mock.get(url, content=content, headers=headers)
        response = await httpx.get(url)
        assert request.called is True
        assert response.headers == httpx.Headers(expected_headers or headers)
        assert response.json() == content


@pytest.mark.asyncio
async def test_raising_content():
    async with respx.HTTPXMock() as httpx_mock:
        url = "https://foo.bar/"
        request = httpx_mock.get(url, content=httpx.ConnectTimeout())
        with pytest.raises(httpx.ConnectTimeout):
            await httpx.get(url)

        assert request.called is True
        _request, _response = request.calls[-1]
        assert _request is not None
        assert _response is None


@pytest.mark.asyncio
async def test_callable_content():
    async with respx.HTTPXMock() as httpx_mock:
        url_pattern = re.compile(r"https://foo.bar/(?P<slug>\w+)/")
        content = lambda request, slug: f"hello {slug}"
        request = httpx_mock.get(url_pattern, content=content)
        response = await httpx.get("https://foo.bar/world/")
        assert request.called is True
        assert response.status_code == 200
        assert response.text == "hello world"


@pytest.mark.asyncio
async def test_request_callback():
    def callback(request, response):
        if request.url.host == "foo.bar":
            response.headers["X-Foo"] = "bar"
            response.content = lambda request, name: f"hello {name}"
            response.context["name"] = "lundberg"
            return response

    async with respx.HTTPXMock(assert_all_called=False) as httpx_mock:
        request = httpx_mock.request(
            callback, status_code=202, headers={"X-Ham": "spam"}
        )
        response = await httpx.get("https://foo.bar/")

        assert request.called is True
        assert request.pass_through is None
        assert response.status_code == 202
        assert response.headers == httpx.Headers(
            {"Content-Type": "text/plain", "X-Ham": "spam", "X-Foo": "bar"}
        )
        assert response.text == "hello lundberg"

        with pytest.raises(ValueError):
            httpx_mock.request(lambda req, res: "invalid")
            await httpx.get("https://ham.spam/")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"method": "GET", "url": "https://example.org/", "pass_through": True}, True,),
        ({"method": lambda request, response: request}, None),
    ],
)
async def test_pass_through(parameters, expected):
    async with respx.HTTPXMock() as httpx_mock:
        request = httpx_mock.request(**parameters)

        with asynctest.mock.patch(
            "asyncio.open_connection",
            side_effect=ConnectionRefusedError("test request blocked"),
        ) as open_connection:
            with pytest.raises(ConnectionRefusedError):
                await httpx.get("https://example.org/")

        assert open_connection.called is True
        assert request.called is True
        assert request.pass_through is expected


@respx.mock
@pytest.mark.asyncio
async def test_parallel_requests():
    async def content(request, page):
        await asyncio.sleep(0.2 if page == "one" else 0.1)
        return page

    url_pattern = re.compile(r"https://foo/(?P<page>\w+)/$")
    respx.get(url_pattern, content=content)

    responses = await asyncio.gather(
        httpx.get("https://foo/one/"), httpx.get("https://foo/two/")
    )
    response_one, response_two = responses

    assert response_one.text == "one"
    assert response_two.text == "two"
    assert respx.stats.call_count == 2
