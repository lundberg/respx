import os

import pytest

import respx

pytestmark = pytest.mark.skipif(
    os.environ.get("PASS_THROUGH") is None, reason="Remote pass-through disabled"
)


@pytest.mark.parametrize(
    "using,client_lib,call_count",
    [
        ("httpcore", "httpx", 2),  # TODO: AsyncConnectionPool + AsyncHTTPConnection
        ("httpx", "httpx", 1),
    ],
)
def test_remote_pass_through(using, client_lib, call_count):  # pragma: nocover
    with respx.mock(using=using) as respx_mock:
        # Mock pass-through calls
        url = "https://httpbin.org/post"
        route = respx_mock.post(url, json__foo="bar").pass_through()

        # Make external pass-through call
        client = __import__(client_lib)
        response = client.post(url, json={"foo": "bar"})

        # Assert response is correct library model
        assert isinstance(response, client.Response)

        assert response.status_code == 200
        assert response.content is not None
        assert len(response.content) > 0
        assert "Content-Length" in response.headers
        assert int(response.headers["Content-Length"]) > 0
        assert response.json()["json"] == {"foo": "bar"}

        assert respx_mock.calls.last.request.url == url
        assert respx_mock.calls.last.has_response is False

        assert route.call_count == call_count
        assert respx_mock.calls.call_count == call_count
