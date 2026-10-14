import pytest

import respx
from respx import httpxlib


def test_httpxlib():
    assert httpxlib.httpx.__name__ == ("httpx2" if httpxlib.RESPX_HTTPX2 else "httpx")
    assert httpxlib.httpcore.__name__ == httpxlib.httpx.__name__.replace("x", "core")


def test_use_httpx2(monkeypatch):
    assert httpxlib.use_httpx2("httpx") is False
    assert httpxlib.use_httpx2("httpx2") is True
    with pytest.raises(ImportError, match="Invalid RESPX_HTTPX 'requests'"):
        httpxlib.use_httpx2("requests")

    monkeypatch.setattr(httpxlib, "find_spec", lambda name: object())
    assert httpxlib.use_httpx2(None) is False
    assert httpxlib.use_httpx2("") is False

    monkeypatch.setattr(httpxlib, "find_spec", lambda name: None)
    assert httpxlib.use_httpx2(None) is True


@pytest.mark.parametrize("name", ["httpx", "httpx2"])
async def test_tool_support(name):  # pragma: no cover
    # Both tools are mocked, regardless of the one respx is using
    tool = pytest.importorskip(name)

    async with respx.mock:
        respx.get("https://example.com/sync") % dict(text="sync")
        respx.get("https://example.com/async") % dict(text="async")

        assert tool.get("https://example.com/sync").text == "sync"
        async with tool.AsyncClient() as client:
            response = await client.get("https://example.com/async")
            assert response.text == "async"
