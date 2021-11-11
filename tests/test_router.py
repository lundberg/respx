import warnings

import httpcore
import httpx
import pytest

from respx import Route, Router
from respx.models import AllMockedAssertionError, PassThrough, RouteList
from respx.patterns import Host, M, Method


@pytest.mark.asyncio
async def test_empty_router():
    router = Router()

    request = httpx.Request("GET", "https://example.org/")
    with pytest.raises(AllMockedAssertionError):
        router.resolve(request)

    with pytest.raises(AllMockedAssertionError):
        await router.aresolve(request)


@pytest.mark.asyncio
async def test_empty_router__auto_mocked():
    router = Router(assert_all_mocked=False)

    request = httpx.Request("GET", "https://example.org/")
    resolved = router.resolve(request)

    assert resolved.route is None
    assert resolved.response.status_code == 200

    resolved = await router.aresolve(request)

    assert resolved.route is None
    assert resolved.response.status_code == 200


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
def test_resolve(args, kwargs, expected):
    router = Router(assert_all_mocked=False)
    route = router.route(*args, **kwargs).respond(status_code=201)

    request = httpx.Request(
        "GET", "https://foo.bar/baz/", cookies={"foo": "bar", "ham": "spam"}
    )
    resolved = router.resolve(request)

    assert bool(resolved.route is route) is expected
    if expected:
        assert bool(resolved.response.status_code == 201) is expected
    else:
        assert resolved.response.status_code == 200  # auto mocked


def test_pass_through():
    router = Router(assert_all_mocked=False)
    route = router.get("https://foo.bar/", path="/baz/").pass_through()

    request = httpx.Request("GET", "https://foo.bar/baz/")
    with pytest.raises(PassThrough) as exc_info:
        router.resolve(request)

    assert exc_info.value.origin is route
    assert exc_info.value.origin.is_pass_through

    route.pass_through(False)
    resolved = router.resolve(request)

    assert resolved.route is route
    assert not resolved.route.is_pass_through
    assert resolved.response is not None


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
    resolved = router.resolve(request)

    assert bool(resolved.route is route) is expected
    if expected:
        assert bool(resolved.response.status_code == 201) is expected
    else:
        assert resolved.response.status_code == 200  # auto mocked


@pytest.mark.parametrize(
    "lookups,url,expected",
    [
        ({"url": "//foo.bar/baz/"}, "https://foo.bar/baz/", True),
        ({"url": "all"}, "https://foo.bar/baz/", True),
        ({"url": "all://"}, "https://foo.bar/baz/", True),
        ({"url": "https://*foo.bar"}, "https://foo.bar/baz/", True),
        ({"url": "https://*foo.bar"}, "https://baz.foo.bar/", True),
        ({"url": "https://*.foo.bar"}, "https://foo.bar/baz/", False),
        ({"url": "https://*.foo.bar"}, "https://baz.foo.bar/", True),
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
    response = router.handler(request)
    assert bool(response.status_code == 418) is expected
    assert route.called is expected


def test_mod_response():
    router = Router()
    route1a = router.get("https://foo.bar/baz/") % 409
    route1b = router.get("https://foo.bar/baz/") % 404
    route2 = router.get("https://foo.bar") % dict(status_code=201)
    route3 = router.post("https://fox.zoo/") % httpx.Response(401, json={"error": "x"})

    request = httpx.Request("GET", "https://foo.bar/baz/")
    resolved = router.resolve(request)
    assert resolved.response.status_code == 404
    assert resolved.route is route1b
    assert route1a is route1b

    request = httpx.Request("GET", "https://foo.bar/")
    resolved = router.resolve(request)
    assert resolved.response.status_code == 201
    assert resolved.route is route2

    request = httpx.Request("POST", "https://fox.zoo/")
    resolved = router.resolve(request)
    assert resolved.response.status_code == 401
    assert resolved.response.json() == {"error": "x"}
    assert resolved.route is route3

    with pytest.raises(TypeError, match="Route can only"):
        router.route() % []


@pytest.mark.asyncio
async def test_async_side_effect():
    router = Router()

    async def effect(request):
        return httpx.Response(204)

    router.get("https://foo.bar/").mock(side_effect=effect)

    request = httpx.Request("GET", "https://foo.bar/")
    response = await router.async_handler(request)
    assert response.status_code == 204


def test_side_effect_no_match():
    router = Router()

    def no_match(request):
        request.respx_was_here = True
        return None

    router.get(url__startswith="https://foo.bar/").mock(side_effect=no_match)
    router.get(url__eq="https://foo.bar/baz/").mock(return_value=httpx.Response(204))

    request = httpx.Request("GET", "https://foo.bar/baz/")
    response = router.handler(request)
    assert response.status_code == 204
    assert response.request.respx_was_here is True


def test_side_effect_with_route_kwarg():
    router = Router()

    def foobar(request, route, slug):
        response = httpx.Response(201, json={"id": route.call_count + 1, "slug": slug})
        if route.call_count > 0:
            route.mock(return_value=httpx.Response(501))
        return response

    router.post(path__regex=r"/(?P<slug>\w+)/").mock(side_effect=foobar)

    request = httpx.Request("POST", "https://foo.bar/baz/")
    response = router.handler(request)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "slug": "baz"}

    response = router.handler(request)
    assert response.status_code == 201
    assert response.json() == {"id": 2, "slug": "baz"}

    response = router.handler(request)
    assert response.status_code == 501


def test_side_effect_with_reserved_route_kwarg():
    router = Router()

    def foobar(request, route):
        assert isinstance(route, Route)
        return httpx.Response(202)

    router.get(path__regex=r"/(?P<route>\w+)/").mock(side_effect=foobar)

    with warnings.catch_warnings(record=True) as w:
        request = httpx.Request("GET", "https://foo.bar/baz/")
        response = router.handler(request)
        assert response.status_code == 202
        assert len(w) == 1


def test_side_effect_list():
    router = Router()
    route = router.get("https://foo.bar/").mock(
        return_value=httpx.Response(409),
        side_effect=[httpx.Response(404), httpcore.NetworkError, httpx.Response(201)],
    )

    request = httpx.Request("GET", "https://foo.bar")
    response = router.handler(request)
    assert response.status_code == 404
    assert response.request == request

    request = httpx.Request("GET", "https://foo.bar")
    with pytest.raises(httpcore.NetworkError):
        router.handler(request)

    request = httpx.Request("GET", "https://foo.bar")
    response = router.handler(request)
    assert response.status_code == 201
    assert response.request == request

    with pytest.raises(StopIteration):
        request = httpx.Request("GET", "https://foo.bar")
        router.handler(request)

    route.side_effect = None
    request = httpx.Request("GET", "https://foo.bar")
    response = router.handler(request)
    assert response.status_code == 409
    assert response.request == request


def test_side_effect_exception():
    router = Router()
    router.get("https://foo.bar/").mock(side_effect=httpx.ConnectError)
    router.get("https://ham.spam/").mock(side_effect=httpcore.NetworkError)
    router.get("https://egg.plant/").mock(side_effect=httpcore.NetworkError())

    request = httpx.Request("GET", "https://foo.bar")
    with pytest.raises(httpx.ConnectError) as e:
        router.handler(request)
    assert e.value.request == request

    request = httpx.Request("GET", "https://ham.spam")
    with pytest.raises(httpcore.NetworkError):
        router.handler(request)

    request = httpx.Request("GET", "https://egg.plant")
    with pytest.raises(httpcore.NetworkError):
        router.handler(request)


def test_side_effect_decorator():
    router = Router()

    @router.route(host="ham.spam", path__regex=r"/(?P<slug>\w+)/")
    def foobar(request, slug):
        return httpx.Response(200, json={"slug": slug})

    @router.post("https://example.org/")
    def example(request):
        return httpx.Response(201, json={"message": "OK"})

    request = httpx.Request("GET", "https://ham.spam/egg/")
    response = router.handler(request)
    assert response.status_code == 200
    assert response.json() == {"slug": "egg"}

    request = httpx.Request("POST", "https://example.org/")
    response = router.handler(request)
    assert response.status_code == 201
    assert response.json() == {"message": "OK"}


def test_rollback():
    router = Router()
    route = router.get("https://foo.bar/") % 404
    pattern = route.pattern
    assert route.name is None

    router.snapshot()  # 1. get 404

    route.return_value = httpx.Response(200)
    router.post("https://foo.bar/").mock(
        side_effect=[httpx.Response(400), httpx.Response(201)]
    )

    router.snapshot()  # 2. get 200, post

    _route = router.get("https://foo.bar/", name="foobar")
    _route = router.get("https://foo.bar/baz/", name="foobar")
    assert _route is route
    assert route.name == "foobar"
    assert route.pattern != pattern
    route.return_value = httpx.Response(418)
    request = httpx.Request("GET", "https://foo.bar/baz/")
    response = router.handler(request)
    assert response.status_code == 418

    request = httpx.Request("POST", "https://foo.bar")
    response = router.handler(request)
    assert response.status_code == 400

    assert len(router.routes) == 2
    assert router.calls.call_count == 2
    assert route.call_count == 1
    assert route.return_value.status_code == 418

    router.snapshot()  # 3. directly rollback, should be identical
    router.rollback()
    assert len(router.routes) == 2
    assert router.calls.call_count == 2
    assert route.call_count == 1
    assert route.return_value.status_code == 418

    router.patch("https://foo.bar/")
    assert len(router.routes) == 3

    route.rollback()  # get 200

    assert router.calls.call_count == 2
    assert route.call_count == 0
    assert route.return_value.status_code == 200

    request = httpx.Request("GET", "https://foo.bar")
    response = router.handler(request)
    assert response.status_code == 200

    router.rollback()  # 2. get 404, post

    request = httpx.Request("POST", "https://foo.bar")
    response = router.handler(request)
    assert response.status_code == 400
    assert len(router.routes) == 2

    router.rollback()  # 1. get 404

    assert len(router.routes) == 1
    assert router.calls.call_count == 0
    assert route.return_value is None

    router.rollback()  # Empty inital state

    assert len(router.routes) == 0
    assert route.return_value is None

    # Idempotent
    route.rollback()
    router.rollback()
    assert len(router.routes) == 0
    assert route.name is None
    assert route.pattern == pattern
    assert route.return_value is None


def test_routelist__add():
    routes = RouteList()

    foobar = Route(method="PUT")
    routes.add(foobar, name="foobar")
    assert routes
    assert list(routes) == [foobar]
    assert routes["foobar"] == foobar
    assert routes["foobar"] is routes[0]

    hamspam = Route(method="POST")
    routes.add(hamspam, name="hamspam")
    assert list(routes) == [foobar, hamspam]
    assert routes["hamspam"] == hamspam


def test_routelist__pop():
    routes = RouteList()

    foobar = Route(method="GET")
    hamspam = Route(method="POST")
    routes.add(foobar, name="foobar")
    routes.add(hamspam, name="hamspam")
    assert list(routes) == [foobar, hamspam]

    _foobar = routes.pop("foobar")
    assert _foobar == foobar
    assert list(routes) == [hamspam]

    default = Route()
    route = routes.pop("egg", default)
    assert route is default
    assert list(routes) == [hamspam]

    with pytest.raises(KeyError):
        routes.pop("egg")


def test_routelist__replaces_same_name_and_pattern():
    routes = RouteList()

    foobar1 = Route(method="GET")
    routes.add(foobar1, name="foobar")
    assert list(routes) == [foobar1]

    foobar2 = Route(method="GET")
    routes.add(foobar2, name="foobar")
    assert list(routes) == [foobar2]
    assert routes[0] is foobar1


def test_routelist__replaces_same_name_diff_pattern():
    routes = RouteList()

    foobar1 = Route(method="GET")
    routes.add(foobar1, name="foobar")
    assert list(routes) == [foobar1]

    foobar2 = Route(method="POST")
    routes.add(foobar2, name="foobar")
    assert list(routes) == [foobar2]
    assert routes[0] is foobar1


def test_routelist__replaces_same_pattern_no_name():
    routes = RouteList()

    foobar1 = Route(method="GET")
    routes.add(foobar1)
    assert list(routes) == [foobar1]

    foobar2 = Route(method="GET")
    routes.add(foobar2, name="foobar")
    assert list(routes) == [foobar2]
    assert routes[0] is foobar1


def test_routelist__replaces_same_pattern_diff_name():
    routes = RouteList()

    foobar1 = Route(method="GET")
    routes.add(foobar1, name="name")
    assert list(routes) == [foobar1]

    foobar2 = Route(method="GET")
    routes.add(foobar2, name="foobar")
    assert list(routes) == [foobar2]
    assert routes[0] is foobar1


def test_routelist__replaces_same_name_other_pattern_no_name():
    routes = RouteList()

    foobar1 = Route(method="GET")
    routes.add(foobar1, name="foobar")
    assert list(routes) == [foobar1]

    hamspam = Route(method="POST")
    routes.add(hamspam)

    foobar2 = Route(method="POST")
    routes.add(foobar2, name="foobar")
    assert list(routes) == [foobar2]
    assert routes[0] is foobar1


def test_routelist__replaces_same_name_other_pattern_other_name():
    routes = RouteList()

    foobar1 = Route(method="GET")
    hamspam = Route(method="POST")

    routes.add(foobar1, name="foobar")
    routes.add(hamspam, name="hamspam")
    assert list(routes) == [foobar1, hamspam]

    foobar2 = Route(method="POST")
    routes.add(foobar2, name="foobar")
    assert list(routes) == [foobar2]
    assert routes["foobar"] is foobar1

def test_configure():
    router = Router(assert_all_called=True, assert_all_mocked=True)

    assert router._assert_all_mocked == True
    router.configure(assert_all_mocked=False)
    assert router._assert_all_mocked == False
    router.rollback();
    assert router._assert_all_mocked == True

    assert router._assert_all_called == True
    router.configure(assert_all_called=False)
    assert router._assert_all_called == False
    router.rollback();
    assert router._assert_all_called == True

    old_bases = router._bases
    router.configure(base_url="https://foo.bar/api/")
    assert router._bases != old_bases
    router.rollback();
    assert router._bases == old_bases
