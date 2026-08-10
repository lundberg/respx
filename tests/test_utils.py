import inspect
from datetime import datetime, timezone

from respx.utils import SetCookie, getfuncargspec


class TestSetCookie:
    def test_can_render_all_attributes(self) -> None:
        expires = datetime.fromtimestamp(0, tz=timezone.utc)
        cookie = SetCookie(
            "foo",
            value="bar",
            path="/",
            domain=".example.com",
            expires=expires,
            max_age=44,
            http_only=True,
            same_site="None",
            partitioned=True,
        )
        assert cookie == (
            "Set-Cookie",
            (
                "foo=bar; "
                "Path=/; "
                "Domain=.example.com; "
                "Expires=Thu, 01 Jan 1970 00:00:00 GMT; "
                "Max-Age=44; "
                "HttpOnly; "
                "SameSite=None; "
                "Secure; "
                "Partitioned"
            ),
        )


class TestGetFuncArgspec:
    def test_matches_inspect_getfullargspec(self):
        def func(request, respx_mock, foo: int = 1, *, bar: str = "x"):
            ...

        spec = getfuncargspec(func)
        reference = inspect.getfullargspec(func)

        assert spec.args == reference.args
        assert spec.varargs == reference.varargs
        assert spec.varkw == reference.varkw
        assert spec.defaults == reference.defaults
        assert spec.kwonlyargs == reference.kwonlyargs

    def test_does_not_force_annotation_evaluation(self, monkeypatch):
        def func(
            request,
            respx_mock,
            foo: int = 1,
            *args: int,
            bar: str = "x",
            baz: float,
            **kwargs: int,
        ):
            ...

        # Simulate the Python 3.14 (PEP 649) failure mode where getfullargspec
        # raises because it forces evaluation of annotations that reference
        # names only available under TYPE_CHECKING.
        monkeypatch.setattr(
            inspect,
            "getfullargspec",
            lambda f: (_ for _ in ()).throw(TypeError("unsupported callable")),
        )

        spec = getfuncargspec(func)

        assert spec.args == ["request", "respx_mock", "foo"]
        assert spec.varargs == "args"
        assert spec.varkw == "kwargs"
        assert spec.defaults == (1,)
        assert spec.kwonlyargs == ["bar", "baz"]
        assert spec.kwonlydefaults == {"bar": "x"}
