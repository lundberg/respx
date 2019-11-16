import re

import asynctest
import httpx
import trio
from httpx.concurrency.base import ConcurrencyBackend
from httpx.concurrency.trio import TrioBackend
from httpx.exceptions import ConnectTimeout

import respx


class HTTPXMockTestCase(asynctest.TestCase):
    def test_api(self):
        url = "https://foo/bar/"
        request = respx.request("GET", url, status_code=202)

        self.assertEqual(len(respx.calls), 0)

        respx.start()
        response = httpx.get(url)
        self.assertEqual(len(respx.calls), 1)
        respx.stop()

        self.assertEqual(len(respx.calls), 0)

        self.assertTrue(request.called)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.text, "")

    @respx.activate
    def test_activate_decorator(self):
        respx.get("https://foo/bar/", status_code=202)
        response = httpx.get("https://foo/bar/")
        self.assertEqual(response.status_code, 202)

    def test_activate_contextmanager(self):
        self.assertEqual(len(respx.calls), 0)

        with respx.activate():
            respx.get("https://foo/bar/", status_code=202)
            response = httpx.get("https://foo/bar/")

            self.assertEqual(response.status_code, 202)
            self.assertEqual(len(respx.calls), 1)

        self.assertEqual(len(respx.calls), 0)

    def test_http_methods(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            m = httpx_mock.get(url, status_code=404)
            httpx_mock.post(url, status_code=201)
            httpx_mock.put(url, status_code=202)
            httpx_mock.patch(url, status_code=500)
            httpx_mock.delete(url, status_code=204)
            httpx_mock.head(url, status_code=405)
            httpx_mock.options(url, status_code=501)

            response = httpx.get(url)
            self.assertEqual(response.status_code, 404)
            response = httpx.post(url)
            self.assertEqual(response.status_code, 201)
            response = httpx.put(url)
            self.assertEqual(response.status_code, 202)
            response = httpx.patch(url)
            self.assertEqual(response.status_code, 500)
            response = httpx.delete(url)
            self.assertEqual(response.status_code, 204)
            response = httpx.head(url)
            self.assertEqual(response.status_code, 405)
            response = httpx.options(url)
            self.assertEqual(response.status_code, 501)

            self.assertTrue(m.called)
            self.assertEqual(len(httpx_mock.calls), 7)

    def test_string_url_pattern(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content="foobar")
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    def test_regex_url_pattern(self):
        with respx.HTTPXMock() as httpx_mock:
            url_pattern = re.compile("^https://foo/.*$")
            foobar = httpx_mock.get(url_pattern, content="whatever")
            response = httpx.get("https://foo/bar/")

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "whatever")

    def test_invalid_url_pattern(self):
        with respx.HTTPXMock() as httpx_mock:
            foobar = httpx_mock.get(["invalid"], content="whatever")
            with self.assertRaises(ValueError):
                httpx.get("https://foo/bar/")

        self.assertFalse(foobar.called)

    def test_unknown_url(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.post(url)  # Non-matching method
            response = httpx.get(url)

            self.assertFalse(foobar.called)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers, httpx.Headers({"Content-Type": "text/plain"})
            )
            self.assertEqual(response.text, "")

            self.assertEqual(len(httpx_mock.calls), 1)
            request, response = httpx_mock.calls[-1]
            self.assertIsNotNone(request)
            self.assertIsNotNone(response)

    def test_repeated_pattern(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/baz/"
            one = httpx_mock.post(url, status_code=201)
            two = httpx_mock.post(url, status_code=409)
            response1 = httpx.post(url, json={})
            response2 = httpx.post(url, json={})
            response3 = httpx.post(url, json={})

            self.assertEqual(response1.status_code, 201)
            self.assertEqual(response2.status_code, 409)
            self.assertEqual(response3.status_code, 409)
            self.assertEqual(len(httpx_mock.calls), 3)

            self.assertTrue(one.called)
            self.assertTrue(len(one.calls), 1)
            statuses = [response.status_code for _, response in one.calls]
            self.assertListEqual(statuses, [201])

            self.assertTrue(two.called)
            self.assertTrue(len(two.calls), 2)
            statuses = [response.status_code for _, response in two.calls]
            self.assertListEqual(statuses, [409, 409])

    def test_status_code(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, status_code=404)
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 404)

    def test_content_type(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content_type="foo/bar")
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers({"Content-Type": "foo/bar"}))

    def test_headers(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "foo/bar", "X-Foo": "bar; baz"}
            foobar = httpx_mock.get(url, headers=headers)
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))

        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "foo/bar", "X-Foo": "bar; baz"}
            content_type = "ham/spam"
            foobar = httpx_mock.get(url, content_type=content_type, headers=headers)
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        merged_headers = httpx.Headers(headers)
        merged_headers["Content-Type"] = content_type
        self.assertEqual(response.headers, merged_headers)

    def test_raw_content(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.post(url, content=b"raw content")
            response = httpx.post(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.text, "raw content")

    def test_json_content(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "application/json"}
            content = {"foo": "bar"}
            foobar = httpx_mock.get(url, content=content)  # Headers not passed
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))
        self.assertDictEqual(response.json(), content)

        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "application/json; charset=utf-8"}
            content = ["foo", "bar"]
            foobar = httpx_mock.get(url, headers=headers, content=content)
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))
        self.assertListEqual(response.json(), content)

    def test_raising_content(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content=ConnectTimeout())
            with self.assertRaises(ConnectTimeout):
                httpx.get(url)

        self.assertTrue(foobar.called)
        request, response = foobar.calls[-1]
        self.assertIsNotNone(request)
        self.assertIsNone(response)

    def test_callable_content(self):
        with respx.HTTPXMock() as httpx_mock:
            url_pattern = re.compile(r"https://foo/bar/(?P<id>\d+)/")
            content = lambda request, id: f"foobar #{id}"
            foobar = httpx_mock.get(url_pattern, content=content)
            response = httpx.get("https://foo/bar/123/")

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar #123")

    def test_sync_client(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content="foobar")
            with httpx.Client() as client:
                response = client.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    async def test_async_client(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content="foobar")
            async with httpx.AsyncClient() as client:
                response = await client.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    @asynctest.skipIf(
        not hasattr(ConcurrencyBackend, "open_uds_stream"),
        "not yet implemented in httpx",
    )
    async def test_uds(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content="foobar")
            async with httpx.AsyncClient(uds="/var/run/foobar.sock") as client:
                response = await client.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    def test_alias(self):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, alias="foobar")
            self.assertIn("foobar", httpx_mock.aliases)
            self.assertEqual(httpx_mock.aliases["foobar"].url, foobar.url)

    def test_exception(self):
        with respx.HTTPXMock() as httpx_mock:
            with asynctest.mock.patch(
                "httpx.client.BaseClient._dispatcher_for_request",
                side_effect=ValueError("mock"),
            ):
                url = "https://foo/bar/1/"
                with self.assertRaises(ValueError):
                    httpx.get(url)

            self.assertEqual(len(httpx_mock.calls), 1)
            request, response = httpx_mock.calls[-1]
            self.assertIsNotNone(request)
            self.assertIsNone(response)

    def test_custom_matcher(self):
        def matcher(request, response):
            if request.url.host == "foo":
                response.content = lambda request, id: f"foobar #{id}"
                response.context["id"] = 123
                return response

        with respx.HTTPXMock() as httpx_mock:
            httpx_mock.request(matcher, status_code=202, headers={"X-Ham": "Spam"})
            response = httpx.get("https://foo/bar/")

            self.assertEqual(response.status_code, 202)
            self.assertEqual(
                response.headers,
                httpx.Headers({"Content-Type": "text/plain", "X-Ham": "Spam"}),
            )
            self.assertEqual(response.text, "foobar #123")

    async def test_stats(self, backend=None):
        with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/1/"
            httpx_mock.get(re.compile("http://some/url"))
            httpx_mock.delete("http://some/url")

            foobar1 = httpx_mock.get(url, status_code=202, alias="get_foobar")
            foobar2 = httpx_mock.delete(url, status_code=200, alias="del_foobar")

            self.assertFalse(foobar1.called)
            self.assertEqual(len(foobar1.calls), 0)
            self.assertEqual(len(httpx_mock.calls), 0)

            async with httpx.AsyncClient(backend=backend) as client:
                get_response = await client.get(url)
                del_response = await client.delete(url)

            self.assertTrue(foobar1.called)
            self.assertTrue(foobar2.called)
            self.assertEqual(len(foobar1.calls), 1)
            self.assertEqual(len(foobar2.calls), 1)

            _request, _response = foobar1.calls[-1]
            self.assertIsNotNone(_request)
            self.assertIsNotNone(_response)
            self.assertEqual(_request.method, "GET")
            self.assertEqual(_request.url, url)
            self.assertEqual(_response.status_code, 202)
            self.assertEqual(_response.status_code, get_response.status_code)

            _request, _response = foobar2.calls[-1]
            self.assertIsNotNone(_request)
            self.assertIsNotNone(_response)
            self.assertEqual(_request.method, "DELETE")
            self.assertEqual(_request.url, url)
            self.assertEqual(_response.status_code, 200)
            self.assertEqual(_response.status_code, del_response.status_code)

            self.assertEqual(len(httpx_mock.calls), 2)
            self.assertEqual(httpx_mock.calls[0], foobar1.calls[-1])
            self.assertEqual(httpx_mock.calls[1], foobar2.calls[-1])

            alias = httpx_mock.aliases["get_foobar"]
            self.assertEqual(alias, foobar1)
            self.assertEqual(alias.alias, foobar1.alias)

            alias = httpx_mock["del_foobar"]
            self.assertEqual(alias, foobar2)
            self.assertEqual(alias.alias, foobar2.alias)

    def test_trio_backend(self):
        trio.run(self.test_stats, TrioBackend())
