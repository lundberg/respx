import httpcore
import httpx
import pytest

from respx import MockResponse, Route, Router
from respx.patterns import Host, M, Method


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
def test_match_and_resolve(args, kwargs, expected):
    router = Router(assert_all_mocked=False)
    route = router.route(*args, **kwargs).respond(status_code=201)

    request = httpx.Request("GET", "https://foo.bar/baz/")
    matched_route, response = router.match(request)

    assert bool(matched_route is route) is expected
    if expected:
        assert bool(response.status_code == 201) is expected
    else:
        assert not response

    response = router.resolve(request)
    assert bool(response.status_code == 201) is expected


def test_pass_through():
    router = Router(assert_all_mocked=False)
    route = router.route(method="GET").pass_through()

    request = httpx.Request("GET", "https://foo.bar/baz/")
    matched_route, response = router.match(request)

    assert matched_route is route
    assert matched_route.is_pass_through
    assert response is request

    route.pass_through(False)
    matched_route, response = router.match(request)

    assert matched_route is route
    assert not matched_route.is_pass_through
    assert response is not None


def test_route_hash():
    route = Route()
    assert not route.is_pass_through
    assert hash(route) == id(route)

    callback = lambda req, res: req  # pragma: nocover
    route.side_effect(callback)
    assert not route.is_pass_through
    assert route.has_side_effect
    assert hash(route) == hash(callback)

    route.pass_through()
    assert route.is_pass_through
    assert not route.has_side_effect
    assert hash(route) == 1

    route.pass_through(False)
    assert not route.is_pass_through
    assert hash(route) == 0

    route.pass_through(None)
    assert not route.is_pass_through
    assert hash(route) == id(route)

    request = httpx.Request("GET", "https://foo.bar/baz/")
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

    request = httpx.Request("GET", url)
    matched_route, response = router.match(request)

    assert bool(matched_route is route) is expected
    if expected:
        assert bool(response.status_code == 201) is expected
    else:
        assert not response

    response = router.resolve(request)
    assert bool(response.status_code == 201) is expected


def test_mod_response():
    router = Router()
    route1a = router.get("https://foo.bar") % 404
    route1b = router.get("https://foo.bar") % dict(status_code=201)
    route2 = router.get("https://ham.spam/egg/") % MockResponse(202)
    route3 = router.post("https://fox.zoo/") % httpx.Response(401, json={"error": "x"})

    request = httpx.Request("GET", "https://foo.bar")
    matched_route, response = router.match(request)
    assert response.status_code == 404
    assert matched_route is route1a

    request = httpx.Request("GET", "https://foo.bar")
    matched_route, response = router.match(request)
    assert response.status_code == 201
    assert matched_route is route1b
    assert route1a is route1b

    request = httpx.Request("GET", "https://ham.spam/egg/")
    matched_route, response = router.match(request)
    assert response.status_code == 202
    assert matched_route is route2

    request = httpx.Request("POST", "https://fox.zoo/")
    matched_route, response = router.match(request)
    assert response.status_code == 401
    assert response.json() == {"error": "x"}
    assert matched_route is route3


def test_side_effect_list():
    router = Router()
    router.get("https://foo.bar/").side_effect(
        [httpx.Response(404), httpx.Response(201)]
    )

    request = httpx.Request("GET", "https://foo.bar")
    response = router.resolve(request)
    assert response.status_code == 404
    assert response.request == request

    request = httpx.Request("GET", "https://foo.bar")
    response = router.resolve(request)
    assert response.status_code == 201
    assert response.request == request


def test_side_effect_exception():
    router = Router()
    router.get("https://foo.bar/").side_effect(httpx.ConnectError)
    router.get("https://ham.spam/").side_effect(httpcore.NetworkError)
    router.get("https://egg.plant/").side_effect(httpcore.NetworkError())

    request = httpx.Request("GET", "https://foo.bar")
    with pytest.raises(httpx.ConnectError) as e:
        router.resolve(request)
    assert e.value.request == request

    request = httpx.Request("GET", "https://ham.spam")
    with pytest.raises(httpcore.NetworkError) as e:
        router.resolve(request)

    request = httpx.Request("GET", "https://egg.plant")
    with pytest.raises(httpcore.NetworkError) as e:
        router.resolve(request)


def test_side_effect_decorator():
    router = Router()

    @router.route(host="ham.spam", path__regex=r"/(?P<slug>\w+)/")
    def foobar(request, slug):
        return httpx.Response(200, json={"slug": slug})

    @router.post("https://example.org/")
    def example(request):
        return httpx.Response(201, json={"message": "OK"})

    request = httpx.Request("GET", "https://ham.spam/egg/")
    response = router.resolve(request)
    assert response.status_code == 200
    assert response.json() == {"slug": "egg"}

    request = httpx.Request("POST", "https://example.org/")
    response = router.resolve(request)
    assert response.status_code == 201
    assert response.json() == {"message": "OK"}
