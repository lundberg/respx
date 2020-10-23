import re

import httpx
import pytest

from respx.models import Request
from respx.patterns import (
    URL,
    BaseURL,
    Host,
    Lookup,
    M,
    Method,
    Params,
    Path,
    Port,
    Scheme,
)


def encode(request: httpx.Request) -> Request:
    return (
        request.method.encode(),
        request.url.raw,
        request.headers.raw,
        request.stream,
    )


def test_bitwise_and():
    pattern = Method("GET") & Host("foo.bar")
    request = encode(httpx.Request("GET", "https://foo.bar/"))
    match = pattern.match(request)
    assert match
    assert bool(match) is True
    assert not ~match


@pytest.mark.parametrize(
    "method,url,expected",
    [
        ("GET", "https://foo.bar/", True),
        ("GET", "https://foo.bar/baz/", False),
        ("POST", "https://foo.bar/", True),
        ("POST", "https://ham.spam/", True),
        ("PATCH", "https://foo.bar/", True),
        ("PUT", "https://foo.bar/", False),
    ],
)
def test_bitwise_operators(method, url, expected):
    pattern = (
        (Method("GET") | Method("post") | Method("Patch")) & URL("https://foo.bar/")
    ) | (Method("POST") & ~URL("https://foo.bar/"))
    request = encode(httpx.Request(method, url))
    assert bool(pattern.match(request)) is expected
    assert bool(~pattern.match(request)) is not expected


def test_match_context():
    request = encode(httpx.Request("GET", "https://foo.bar/baz/?ham=spam"))
    pattern = (
        URL(r"https?://foo.bar/(?P<slug>\w+)/", Lookup.REGEX)
        & URL(r"https://(?P<host>[^/]+)/baz/", Lookup.REGEX)
        & Params({"ham": "spam"})
    )
    match = pattern.match(request)
    assert bool(match)
    assert match.context == {"host": "foo.bar", "slug": "baz"}


@pytest.mark.parametrize(
    "scheme,expected",
    [
        ("https", True),
        ("HTTPS", True),
        ("http", False),
    ],
)
def test_scheme_pattern(scheme, expected):
    _request = httpx.Request("GET", "https://foo.bar/")
    for request in (_request, encode(_request)):
        assert bool(Scheme(scheme).match(request)) is expected


@pytest.mark.parametrize(
    "host,expected",
    [
        ("foo.bar", True),
        ("Foo.bar", True),
        ("ham.spam", False),
    ],
)
def test_host_pattern(host, expected):
    _request = httpx.Request("GET", "https://foo.bar/")
    for request in (_request, encode(_request)):
        assert bool(Host(host).match(request)) is expected


@pytest.mark.parametrize(
    "port,url,expected",
    [
        (443, "https://foo.bar/", True),
        (80, "https://foo.bar/", False),
        (80, "http://foo.bar/", True),
        (8080, "https://foo.bar:8080/baz/", True),
        (22, "//foo.bar:22/baz/", True),
        (None, "//foo.bar/", True),
    ],
)
def test_port_pattern(port, url, expected):
    _request = httpx.Request("GET", url)
    for request in (_request, encode(_request)):
        assert bool(Port(port).match(request)) is expected


def test_path_pattern():
    _request = httpx.Request("GET", "https://foo.bar/baz/")
    for request in (_request, encode(_request)):
        assert Path("/baz/").match(request)
        assert not Path("/ham/").match(request)

    _request = httpx.Request("GET", "https://foo.bar/baz/?ham=spam")
    for request in (_request, encode(_request)):
        assert Path("/baz/").match(request)
        assert not Path("/ham/").match(request)

        match = Path(r"/(?P<slug>\w+)/", Lookup.REGEX).match(request)
        assert bool(match) is True
        assert match.context == {"slug": "baz"}

        match = Path(re.compile(r"^/ham/"), Lookup.REGEX).match(request)
        assert bool(match) is False


@pytest.mark.parametrize(
    "params,url,expected",
    [
        ("", "https://foo.bar/", True),
        ("x=1", "https://foo.bar/?x=1", True),
        ("x=1&y=2", "https://foo.bar/?x=1", False),
    ],
)
def test_params_pattern(params, url, expected):
    _request = httpx.Request("GET", url)
    for request in (_request, encode(_request)):
        assert bool(Params(params).match(request)) is expected


@pytest.mark.parametrize(
    "lookup,url,context,expected",
    [
        (Lookup.REGEX, r"https?://foo.bar/(?P<slug>\w+)/", {"slug": "baz"}, True),
        (Lookup.REGEX, re.compile(r"^https://foo.bar/.+$"), {}, True),
        (Lookup.REGEX, r"https://ham.spam/baz/", {}, False),
        (Lookup.EXACT, "https://foo.bar/baz/", {}, True),
        (Lookup.EXACT, "https://foo.bar/ham/", {}, False),
        (Lookup.STARTS_WITH, "https://foo.bar/b", {}, True),
    ],
)
def test_url_pattern(lookup, url, context, expected):
    _request = httpx.Request("GET", "https://foo.bar/baz/")
    for request in (_request, encode(_request)):
        match = URL(url, lookup=lookup).match(request)
        assert bool(match) is expected
        assert match.context == context


@pytest.mark.parametrize(
    "url,expected",
    [
        (httpx.URL("https://foo.bar/baz/"), True),
        ("https://foo.bar/baz/", True),
        ("https://foo.bar/baz/?egg=yolk&ham=spam", True),
        ("https://foo.bar/baz/?egg=yolk", True),
        ("//foo.bar/baz/", True),
        ("https://foo.bar:443/baz/", True),
        ("http://foo.bar/", False),
        ("https://ham.spam/", False),
        ("https://foo.bar/", False),
        ("https://foo.bar:80/baz/", False),
        ("https://foo.bar/ham/", False),
    ],
)
def test_url_pattern__eq(url, expected):
    _request = httpx.Request("GET", "https://foo.bar/baz/?ham=spam&egg=yolk")
    for request in (_request, encode(_request)):
        assert bool(URL(url).match(request)) is expected


def test_url_pattern_invalid():
    with pytest.raises(ValueError, match="Invalid"):
        URL("")


def test_invalid_pattern():
    with pytest.raises(ValueError, match="is not a valid Pattern"):
        M(foo="baz")
    with pytest.raises(ValueError, match="is not a valid Lookup"):
        Scheme("http", Lookup.REGEX)
    with pytest.raises(ValueError, match="is not a valid Lookup"):
        M(scheme__baz="zoo")


@pytest.mark.parametrize(
    "base_url,expected",
    [
        ("https://foo.bar", True),
        ("https://foo.bar", True),
        ("https://foo.bar/", True),
        ("https://foo.bar/baz", True),
        ("https://foo.bar/baz/", True),
        ("http://foo.bar/baz/", False),
        ("https://ham.spam/baz/", False),
        ("https://foo.bar/ham/", False),
    ],
)
def test_baseurl_pattern(base_url, expected):
    _request = httpx.Request("GET", "https://foo.bar/baz/zoo/?ham=spam&egg=yolk")
    for request in (_request, encode(_request)):
        assert bool(BaseURL(base_url).match(request)) is expected


def test_baseurl_pattern_invalid():
    with pytest.raises(ValueError, match="Invalid"):
        BaseURL("/foo/")
    with pytest.raises(ValueError, match="Invalid"):
        BaseURL(re.compile("/foo/"))
