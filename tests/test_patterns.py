import re

import httpx
import pytest

from respx.patterns import (
    URL,
    Cookies,
    Headers,
    Host,
    Lookup,
    M,
    Method,
    Params,
    Path,
    Port,
    Scheme,
    merge_patterns,
    parse_url_patterns,
)
from respx.types import Request


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
    "lookup,value,expected",
    [
        (Lookup.EQUAL, "GET", True),
        (Lookup.EQUAL, "POST", False),
        (Lookup.IN, ["GET", "POST"], True),
        (Lookup.IN, ["POST", "PUT"], False),
    ],
)
def test_method_pattern(lookup, value, expected):
    _request = httpx.Request("GET", "https://foo.bar/")
    for request in (_request, encode(_request)):
        assert bool(Method(value, lookup=lookup).match(request)) is expected


@pytest.mark.parametrize(
    "lookup,headers,request_headers,expected",
    [
        (Lookup.CONTAINS, {"X-Foo": "bar"}, {"x-foo": "bar"}, True),
        (Lookup.CONTAINS, {"content-type": "text/plain"}, "", False),
    ],
)
def test_headers_pattern(lookup, headers, request_headers, expected):
    _request = httpx.Request(
        "GET", "http://foo.bar/", headers=request_headers, json={"foo": "bar"}
    )
    for request in (_request, encode(_request)):
        assert bool(Headers(headers, lookup=lookup).match(request)) is expected


@pytest.mark.parametrize(
    "lookup,cookies,request_cookies,expected",
    [
        (Lookup.CONTAINS, {"foo": "bar"}, {"ham": "spam", "foo": "bar"}, True),
        (Lookup.CONTAINS, {"foo": "bar"}, {"ham": "spam"}, False),
        (Lookup.EQUAL, {"foo": "bar"}, {"foo": "bar"}, True),
        (Lookup.EQUAL, [("foo", "bar")], {"foo": "bar"}, True),
        (Lookup.EQUAL, {}, {}, True),
        (Lookup.EQUAL, {}, None, True),
        (Lookup.EQUAL, {"foo": "bar"}, {"ham": "spam"}, False),
    ],
)
def test_cookies_pattern(lookup, cookies, request_cookies, expected):
    _request = httpx.Request(
        "GET", "http://foo.bar/", cookies=request_cookies, json={"foo": "bar"}
    )
    for request in (_request, encode(_request)):
        assert bool(Cookies(cookies, lookup=lookup).match(request)) is expected


@pytest.mark.parametrize(
    "lookup,scheme,expected",
    [
        (Lookup.EQUAL, "https", True),
        (Lookup.EQUAL, "HTTPS", True),
        (Lookup.EQUAL, "http", False),
        (Lookup.IN, ["http", "https"], True),
    ],
)
def test_scheme_pattern(lookup, scheme, expected):
    _request = httpx.Request("GET", "https://foo.bar/")
    for request in (_request, encode(_request)):
        assert bool(Scheme(scheme, lookup=lookup).match(request)) is expected


@pytest.mark.parametrize(
    "host,expected",
    [
        ("foo.bar", True),
        ("ham.spam", False),
    ],
)
def test_host_pattern(host, expected):
    _request = httpx.Request("GET", "https://foo.bar/")
    for request in (_request, encode(_request)):
        assert bool(Host(host).match(request)) is expected


@pytest.mark.parametrize(
    "lookup,port,url,expected",
    [
        (Lookup.EQUAL, 443, "https://foo.bar/", True),
        (Lookup.EQUAL, 80, "https://foo.bar/", False),
        (Lookup.EQUAL, 80, "http://foo.bar/", True),
        (Lookup.EQUAL, 8080, "https://foo.bar:8080/baz/", True),
        (Lookup.EQUAL, 8080, "https://foo.bar/baz/", False),
        (Lookup.EQUAL, 22, "//foo.bar:22/baz/", True),
        (Lookup.EQUAL, None, "//foo.bar/", True),
        (Lookup.IN, [80, 443], "http://foo.bar/", True),
        (Lookup.IN, [80, 443], "https://foo.bar/", True),
        (Lookup.IN, [80, 443], "https://foo.bar:8080/", False),
    ],
)
def test_port_pattern(lookup, port, url, expected):
    _request = httpx.Request("GET", url)
    for request in (_request, encode(_request)):
        assert bool(Port(port, lookup=lookup).match(request)) is expected


def test_path_pattern():
    _request = httpx.Request("GET", "https://foo.bar")
    for request in (_request, encode(_request)):
        assert Path("/").match(request)

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

    _request = httpx.Request("GET", "https://foo.bar/baz/")
    for request in (_request, encode(_request)):
        assert Path(["/egg/", "/baz/"], lookup=Lookup.IN).match(request)


@pytest.mark.parametrize(
    "lookup,params,url,expected",
    [
        (Lookup.CONTAINS, "", "https://foo.bar/", True),
        (Lookup.CONTAINS, "x=1", "https://foo.bar/?x=1", True),
        (Lookup.CONTAINS, "y=2", "https://foo.bar/?x=1", False),
        (Lookup.CONTAINS, "x=1&y=2", "https://foo.bar/?x=1", False),
        (Lookup.EQUAL, "", "https://foo.bar/", True),
        (Lookup.EQUAL, "x=1", "https://foo.bar/?x=1", True),
        (Lookup.EQUAL, "y=2", "https://foo.bar/?x=1", False),
        (Lookup.EQUAL, "x=1&y=2", "https://foo.bar/?x=1", False),
    ],
)
def test_params_pattern(lookup, params, url, expected):
    _request = httpx.Request("GET", url)
    for request in (_request, encode(_request)):
        assert bool(Params(params, lookup=lookup).match(request)) is expected


@pytest.mark.parametrize(
    "lookup,url,context,expected",
    [
        (Lookup.REGEX, r"https?://foo.bar/(?P<slug>\w+)/", {"slug": "baz"}, True),
        (Lookup.REGEX, re.compile(r"^https://foo.bar/.+$"), {}, True),
        (Lookup.REGEX, r"https://ham.spam/baz/", {}, False),
        (Lookup.EQUAL, "https://foo.bar/baz/", {}, True),
        (Lookup.EQUAL, "https://foo.bar/ham/", {}, False),
        (Lookup.STARTS_WITH, "https://foo.bar/b", {}, True),
        (Lookup.STARTS_WITH, "http://foo.bar/baz/", {}, False),
    ],
)
def test_url_pattern(lookup, url, context, expected):
    _request = httpx.Request("GET", "https://foo.bar/baz/")
    for request in (_request, encode(_request)):
        match = URL(url, lookup=lookup).match(request)
        assert bool(match) is expected
        assert match.context == context


def test_url_pattern_invalid():
    with pytest.raises(ValueError, match="Invalid"):
        URL(["invalid"])


def test_url_pattern_hash():
    p = Host("foo.bar") & Path("/baz/")
    assert M(url="//foo.bar/baz/") == p
    p = Scheme("https") & Host("foo.bar") & Path("/baz/")
    assert M(url="https://foo.bar/baz/") == p


def test_invalid_pattern():
    with pytest.raises(KeyError, match="is not a valid Pattern"):
        M(foo="baz")
    with pytest.raises(NotImplementedError, match="is not a valid Lookup"):
        Scheme("http", Lookup.REGEX)
    with pytest.raises(ValueError, match="is not a valid Lookup"):
        M(scheme__baz="zoo")


def test_iter_pattern():
    pattern = M(
        Method("GET") & Path("/baz/") | ~Params("x=y"), url="https://foo.bar:88/"
    )
    patterns = list(iter(pattern))
    assert len(patterns) == 6
    assert set(patterns) == {
        Method("GET"),
        Scheme("https"),
        Host("foo.bar"),
        Port(88),
        Path("/baz/"),
        Params("x=y"),
    }


def test_parse_url_patterns():
    patterns = parse_url_patterns("https://foo.bar/ham/spam/?egg=yolk")
    assert patterns == {
        "scheme": Scheme("https"),
        "host": Host("foo.bar"),
        "path": Path("/ham/spam/"),
        "params": Params({"egg": "yolk"}, Lookup.EQUAL),
    }

    patterns = parse_url_patterns("https://foo.bar/ham/spam/?egg=yolk", exact=False)
    assert patterns == {
        "scheme": Scheme("https"),
        "host": Host("foo.bar"),
        "path": Path("/ham/spam/", Lookup.STARTS_WITH),
        "params": Params({"egg": "yolk"}, Lookup.CONTAINS),
    }


def test_merge_patterns():
    pattern = Method("GET") & Path("/spam/")
    base = Path("/ham/", Lookup.STARTS_WITH)
    merged_pattern = merge_patterns(pattern, path=base)
    assert any([p.base == base for p in iter(merged_pattern)])