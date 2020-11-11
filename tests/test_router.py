import httpcore
import httpx
import pytest

from respx import Router
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
        (tuple(), dict(headers={"host": "foo.bar"}), True),
        (tuple(), dict(headers={"Content-Type": "text/plain"}), False),
        (tuple(), dict(headers={"cookie": "foo=bar"}), False),
        (tuple(), dict(cookies={"ham": "spam"}), True),
    ],
)
def test_match_and_resolve(args, kwargs, expected):
    router = Router(assert_all_mocked=False)
    route = router.route(*args, **kwargs).respond(status_code=201)

    request = httpx.Request(
        "GET", "https://foo.bar/baz/", cookies={"foo": "bar", "ham": "spam"}
    )
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
    route = router.get("https://foo.bar/", path="/baz/").pass_through()

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


@pytest.mark.parametrize(
    "url,lookups,expected",
    [
        ("https://foo.bar/api/baz/", {"url": "/baz/"}, True),
        ("https://foo.bar/api/baz/", {"path__regex": r"^/(?P<slug>\w+)/$"}, True),
        ("http://foo.bar/api/baz/", {"url": "/baz/"}, False),
        ("https://ham.spam/api/baz/", {"url": "/baz/"}, False),
        ("https://foo.bar/baz/", {"url": "/baz/"}, False),
    ],
)
def test_base_url(url, lookups, expected):
    router = Router(base_url="https://foo.bar/api/", assert_all_mocked=False)
    route = router.get(**lookups).respond(201)

    request = httpx.Request("GET", url)
    matched_route, response = router.match(request)

    assert bool(matched_route is route) is expected
    if expected:
        assert bool(response.status_code == 201) is expected
    else:
        assert not response

    response = router.resolve(request)
    assert bool(response.status_code == 201) is expected


@pytest.mark.parametrize(
    "lookups,url,expected",
    [
        ({"url": "//foo.bar/baz/"}, "https://foo.bar/baz/", True),
        ({"url__eq": "https://foo.bar/baz/"}, "https://foo.bar/baz/", True),
        ({"url__eq": "https://foo.bar/baz/"}, "http://foo.bar/baz/", False),
        ({"url__eq": "https://foo.bar"}, "https://foo.bar/", True),
        ({"url__eq": "https://foo.bar/"}, "https://foo.bar", True),
        (
            {"url": "https://foo.bar/", "path__regex": r"/(?P<slug>\w+)/"},
            "https://foo.bar/baz/",
            True,
        ),
    ],
)
def test_url_pattern_lookup(lookups, url, expected):
    router = Router(assert_all_mocked=False)
    route = router.get(**lookups) % 418
    request = httpx.Request("GET", url)
    response = router.resolve(request)
    assert bool(response.status_code == 418) is expected
    assert route.called is expected


def test_mod_response():
    router = Router()
    route1a = router.get("https://foo.bar/baz/") % 409
    route1b = router.get("https://foo.bar/baz/") % 404
    route2 = router.get("https://foo.bar") % dict(status_code=201)
    route3 = router.post("https://fox.zoo/") % httpx.Response(401, json={"error": "x"})

    request = httpx.Request("GET", "https://foo.bar/baz/")
    matched_route, response = router.match(request)
    assert response.status_code == 404
    assert matched_route is route1b
    assert route1a is route1b

    request = httpx.Request("GET", "https://foo.bar/")
    matched_route, response = router.match(request)
    assert response.status_code == 201
    assert matched_route is route2

    request = httpx.Request("POST", "https://fox.zoo/")
    matched_route, response = router.match(request)
    assert response.status_code == 401
    assert response.json() == {"error": "x"}
    assert matched_route is route3

    with pytest.raises(ValueError, match="Route can only"):
        router.route() % []


def test_side_effect_no_match():
    router = Router()

    def no_match(request):
        request.respx_was_here = True
        return None

    router.get(url__startswith="https://foo.bar/").mock(side_effect=no_match)
    router.get(url__eq="https://foo.bar/baz/").mock(return_value=httpx.Response(204))

    request = httpx.Request("GET", "https://foo.bar/baz/")
    response = router.resolve(request)
    assert response.status_code == 204
    assert response.request.respx_was_here is True


def test_side_effect_list():
    router = Router()
    route = router.get("https://foo.bar/").mock(
        return_value=httpx.Response(409),
        side_effect=[httpx.Response(404), httpcore.NetworkError, httpx.Response(201)],
    )

    request = httpx.Request("GET", "https://foo.bar")
    response = router.resolve(request)
    assert response.status_code == 404
    assert response.request == request

    request = httpx.Request("GET", "https://foo.bar")
    with pytest.raises(httpcore.NetworkError):
        router.resolve(request)

    request = httpx.Request("GET", "https://foo.bar")
    response = router.resolve(request)
    assert response.status_code == 201
    assert response.request == request

    with pytest.raises(StopIteration):
        request = httpx.Request("GET", "https://foo.bar")
        router.resolve(request)

    route.side_effect = None
    request = httpx.Request("GET", "https://foo.bar")
    response = router.resolve(request)
    assert response.status_code == 409
    assert response.request == request


def test_side_effect_exception():
    router = Router()
    router.get("https://foo.bar/").mock(side_effect=httpx.ConnectError)
    router.get("https://ham.spam/").mock(side_effect=httpcore.NetworkError)
    router.get("https://egg.plant/").mock(side_effect=httpcore.NetworkError())

    request = httpx.Request("GET", "https://foo.bar")
    with pytest.raises(httpx.ConnectError) as e:
        router.resolve(request)
    assert e.value.request == request

    request = httpx.Request("GET", "https://ham.spam")
    with pytest.raises(httpcore.NetworkError):
        router.resolve(request)

    request = httpx.Request("GET", "https://egg.plant")
    with pytest.raises(httpcore.NetworkError):
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


def test_rollback():
    router = Router()
    route = router.get("https://foo.bar/") % 404

    router.snapshot()

    route.return_value = httpx.Response(418)
    router.post("https://foo.bar/")

    request = httpx.Request("GET", "https://foo.bar")
    response = router.resolve(request)
    assert response.status_code == 418

    assert len(router.routes) == 2
    assert router.calls.call_count == 1
    assert route.call_count == 1
    assert route.return_value.status_code == 418

    route.rollback()

    assert len(router.routes) == 2
    assert router.calls.call_count == 1
    assert route.call_count == 0
    assert route.return_value.status_code == 404

    request = httpx.Request("GET", "https://foo.bar")
    response = router.resolve(request)
    assert response.status_code == 404

    router.rollback()

    assert len(router.routes) == 1
    assert router.calls.call_count == 0
