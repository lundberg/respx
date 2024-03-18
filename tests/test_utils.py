from datetime import datetime, timezone

from respx.utils import SetCookie


def test_set_cookie_header():
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
    assert cookie.header == (
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
