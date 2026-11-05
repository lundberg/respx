from datetime import datetime, timedelta, timezone
from typing import Union

import pytest

from respx.utils import SetCookie


class TestSetCookie:
    @pytest.mark.parametrize(
        "expires",
        [
            datetime(2099, 12, 31, 19, tzinfo=timezone(timedelta(hours=-5))),
            datetime(
                2100, 1, 1, 5, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))
            ),
            datetime(2100, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None),
            "Fri, 01 Jan 2100 00:00:00 GMT",
        ],
    )
    def test_expires_preserves_instant(self, expires: Union[str, datetime]) -> None:
        assert SetCookie("foo", "bar", expires=expires) == (
            "Set-Cookie",
            "foo=bar; Expires=Fri, 01 Jan 2100 00:00:00 GMT",
        )

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
