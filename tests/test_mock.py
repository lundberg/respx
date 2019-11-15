import re

import asynctest
import httpx
import trio
from httpx.concurrency.base import ConcurrencyBackend
from httpx.concurrency.trio import TrioBackend
from httpx.exceptions import ConnectTimeout

import responsex


class HTTPXMockTestCase(asynctest.TestCase):
    def test_api(self):
        url = "https://foo/bar/"
        foobar = responsex.add("GET", url, status_code=202)

        responsex.start()
        response = httpx.get(url)
        responsex.stop()

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.text, "")

    def test_string_url_pattern(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, content="foobar")
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    def test_regex_url_pattern(self):
        with responsex.HTTPXMock() as httpx_mock:
            url_pattern = re.compile("^https://foo/.*$")
            foobar = httpx_mock.add("GET", url_pattern, content="whatever")
            response = httpx.get("https://foo/bar/")

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "whatever")

    def test_unknown_url(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("POST", url)  # Non-matching method
            response = httpx.get(url)

            self.assertFalse(foobar.called)
            self.assertEqual(response.status_code, 200)
            self.assertDictEqual(
                dict(response.headers.items()), {"content-type": "text/plain"}
            )
            self.assertEqual(response.text, "")

            self.assertEqual(len(httpx_mock.calls), 1)
            (request, response), _ = httpx_mock.calls[-1]
            self.assertIsNotNone(request)
            self.assertIsNotNone(response)

    def test_status_code(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, status_code=404)
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 404)

    def test_content_type(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, content_type="foo/bar")
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers({"Content-Type": "foo/bar"}))

    def test_headers(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "foo/bar", "X-Foo": "bar; baz"}
            foobar = httpx_mock.add("GET", url, headers=headers)
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))

        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "foo/bar", "X-Foo": "bar; baz"}
            content_type = "ham/spam"
            foobar = httpx_mock.add(
                "GET", url, content_type=content_type, headers=headers
            )
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        merged_headers = httpx.Headers(headers)
        merged_headers["Content-Type"] = content_type
        self.assertEqual(response.headers, merged_headers)

    def test_raw_content(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("POST", url, content=b"raw content")
            response = httpx.post(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.text, "raw content")

    def test_json_content(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "application/json"}
            content = {"foo": "bar"}
            foobar = httpx_mock.add("GET", url, content=content)  # Headers not passed
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))
        self.assertDictEqual(response.json(), content)

        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "application/json; charset=utf-8"}
            content = ["foo", "bar"]
            foobar = httpx_mock.add("GET", url, headers=headers, content=content)
            response = httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))
        self.assertListEqual(response.json(), content)

    def test_raising_content(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, content=ConnectTimeout())
            with self.assertRaises(ConnectTimeout):
                httpx.get(url)

        self.assertTrue(foobar.called)
        (request, response), _ = foobar.call_args_list[-1]
        self.assertIsNotNone(request)
        self.assertIsNone(response)

    def test_callable_content(self):
        with responsex.HTTPXMock() as httpx_mock:
            url_pattern = re.compile(r"https://foo/bar/(?P<id>\d+)/")
            content = lambda id: f"foobar #{id}"
            foobar = httpx_mock.add("GET", url_pattern, content=content)
            response = httpx.get("https://foo/bar/123/")

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar #123")

    def test_sync_client(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, content="foobar")
            with httpx.Client() as client:
                response = client.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    async def test_async_client(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, content="foobar")
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
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, content="foobar")
            async with httpx.AsyncClient(uds="/var/run/foobar.sock") as client:
                response = await client.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    def test_alias(self):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.add("GET", url, alias="foobar")
            self.assertIn("foobar", httpx_mock.aliases)
            self.assertEqual(httpx_mock.aliases["foobar"].url, foobar.url)

    def test_exception(self):
        with responsex.HTTPXMock() as httpx_mock:
            with asynctest.mock.patch(
                "httpx.client.BaseClient._dispatcher_for_request",
                side_effect=ValueError("mock"),
            ):
                url = "https://foo/bar/1/"
                with self.assertRaises(ValueError):
                    httpx.get(url)

            self.assertEqual(len(httpx_mock.calls), 1)
            (request, response), _ = httpx_mock.calls[-1]
            self.assertIsNotNone(request)
            self.assertIsNone(response)

    async def test_stats(self, backend=None):
        with responsex.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/1/"
            httpx_mock.add("GET", re.compile("http://some/url"))
            httpx_mock.add("DELETE", "http://some/url")

            foobar1 = httpx_mock.add("GET", url, status_code=202, alias="get_foobar")
            foobar2 = httpx_mock.add("DELETE", url, status_code=200, alias="del_foobar")

            self.assertFalse(foobar1.called)
            self.assertEqual(len(foobar1.call_args_list), 0)
            self.assertEqual(len(httpx_mock.calls), 0)

            async with httpx.AsyncClient(backend=backend) as client:
                get_response = await client.get(url)
                del_response = await client.delete(url)

            self.assertTrue(foobar1.called)
            self.assertTrue(foobar2.called)
            self.assertEqual(len(foobar1.call_args_list), 1)
            self.assertEqual(len(foobar2.call_args_list), 1)

            get_call = foobar1.call_args_list[-1]
            (_request, _response), _ = get_call
            self.assertIsNotNone(_request)
            self.assertIsNotNone(_response)
            self.assertEqual(_request.method, "GET")
            self.assertEqual(_request.url, url)
            self.assertEqual(_response.status_code, 202)
            self.assertEqual(_response.status_code, get_response.status_code)

            del_call = foobar2.call_args_list[-1]
            (_request, _response), _ = del_call
            self.assertIsNotNone(_request)
            self.assertIsNotNone(_response)
            self.assertEqual(_request.method, "DELETE")
            self.assertEqual(_request.url, url)
            self.assertEqual(_response.status_code, 200)
            self.assertEqual(_response.status_code, del_response.status_code)

            self.assertEqual(len(httpx_mock.calls), 2)
            self.assertEqual(httpx_mock.calls[0], foobar1.call_args_list[-1])
            self.assertEqual(httpx_mock.calls[1], foobar2.call_args_list[-1])

            alias = httpx_mock.aliases["get_foobar"]
            self.assertEqual(alias, foobar1)
            self.assertEqual(alias.alias, foobar1.alias)

            alias = httpx_mock["del_foobar"]
            self.assertEqual(alias, foobar2)
            self.assertEqual(alias.alias, foobar2.alias)

    def test_trio_backend(self):
        trio.run(self.test_stats, TrioBackend())
