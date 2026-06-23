import functools
from datetime import datetime, timezone

from respx.utils import SetCookie, get_arg_spec


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


class TestGetArgSpec:
    def test_returns_positional_args_and_defaults(self) -> None:
        def func(a, b, c=3, *args, d, e=5, **kwargs):  # pragma: no cover
            ...

        arg_spec = get_arg_spec(func)
        assert arg_spec.args == ["a", "b", "c"]
        assert arg_spec.defaults == (3,)

    def test_returns_none_defaults_without_defaults(self) -> None:
        def func(a, b):  # pragma: no cover
            ...

        arg_spec = get_arg_spec(func)
        assert arg_spec.args == ["a", "b"]
        assert arg_spec.defaults is None

    def test_follows_wrapped_chain(self) -> None:
        def inner(a, b, respx_mock=None):  # pragma: no cover
            ...

        @functools.wraps(inner)
        def wrapper(*args, **kwargs):  # pragma: no cover
            ...

        # Follows __wrapped__ (inspect.signature's default) so respx detects
        # respx_mock / route declared on a wrapped function.
        arg_spec = get_arg_spec(wrapper)
        assert arg_spec.args == ["a", "b", "respx_mock"]
        assert arg_spec.defaults == (None,)
