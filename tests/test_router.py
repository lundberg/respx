import httpx
import pytest

from respx import MockResponse, Route, Router
from respx.patterns import Host, M, Method


def encode_request(method: str, url: str):
    request = httpx.Request(method, url)
    return (
        request.method.encode("ascii"),
        request.url.raw,
        request.headers.raw,
        request.stream,
    )


@pytest.mark.parametrize(
    "args,kwargs,expected",
    [
        ((Method("GET"), Host("foo.bar")), dict(), True),
        (tuple(), dict(method="GET", host="foo.bar"), True),
        ((Method("GET"),), dict(port=443, url__regex=r"/baz/$"), True),
        ((Method("POST"),), dict(host="foo.bar"), False),
        ((~Method("GET"),), dict(), False),
        ((~M(url__regex=r"/baz/$"),), dict(), False),
    ],
)
def test_match(args, kwargs, expected):
    router = Router(assert_all_mocked=False)
    route = router.route(*args, **kwargs).respond(status_code=201)

    request = httpx.Request("GET", "https://foo.bar/baz/")
    mock_response, matched_route = router.match(request)

    assert bool(matched_route is route) is expected
    assert bool(mock_response.status_code == 201) is expected


def test_pass_through():
    router = Router(assert_all_mocked=False)
    route = router.route(method="GET").pass_through()

    request = encode_request("GET", "https://foo.bar/baz/")
    mock_response, matched_route = router.match(request)

    assert matched_route is route
    assert matched_route.is_pass_through
    assert mock_response is None

    route.pass_through(False)
    mock_response, matched_route = router.match(request)

    assert matched_route is route
    assert not matched_route.is_pass_through
    assert mock_response is not None


def test_route_hash():
    route = Route()
    assert not route.is_pass_through
    assert hash(route) == id(route)

    callback = lambda req, res: req  # pragma: nocover
    route.callback(callback)
    assert not route.is_pass_through
    assert route._callback
    assert hash(route) == hash(callback)

    route.pass_through()
    assert route.is_pass_through
    assert not route._callback
    assert hash(route) == 1

    route.pass_through(False)
    assert not route.is_pass_through
    assert hash(route) == 0

    route.pass_through(None)
    assert not route.is_pass_through
    assert hash(route) == id(route)

    request = encode_request("GET", "https://foo.bar/baz/")
    response = route.match(request)
    assert response is None


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://foo.bar/baz/", True),
        ("https://ham.spam/baz/", False),
    ],
)
def test_base_url(url, expected):
    router = Router(base_url="https://foo.bar/", assert_all_mocked=False)
    route = router.route(method="GET", url="/baz/").respond(201)

    request = encode_request("GET", url)
    mock_response, matched_route = router.match(request)

    assert bool(mock_response.status_code == 201) is expected
    assert bool(matched_route is route) is expected


def test_mod_response():
    router = Router()
    route1 = router.get("https://foo.bar") % dict(status_code=201)
    route2 = router.get("https://ham.spam/egg/") % MockResponse(202)
    route3 = router.post("https://fox.zoo/") % httpx.Response(401, json={"error": "x"})

    request = encode_request("GET", "https://foo.bar")
    mock_response, matched_route = router.match(request)

    assert mock_response.status_code == 201
    assert matched_route is route1

    request = encode_request("GET", "https://ham.spam/egg/")
    mock_response, matched_route = router.match(request)

    assert mock_response.status_code == 202
    assert matched_route is route2

    request = encode_request("POST", "https://fox.zoo/")
    response, matched_route = router.match(request)

    assert response.status_code == 401
    assert response.json() == {"error": "x"}
    assert matched_route is route3
