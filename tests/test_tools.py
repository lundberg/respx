import sys

import pytest

import respx

pytestmark = pytest.mark.skipif(sys.version_info < (3, 10), reason="Old python version")


def test_httpx2_support():  # pragma: no cover
    import httpx2  # type: ignore[import-not-found]

    with respx.mock:
        respx.get("https://example.com/httpx").respond(text="2")
        response = httpx2.get("https://example.com/httpx")
        assert response.text == "2"
