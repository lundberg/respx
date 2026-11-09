from datetime import datetime, timezone

import httpx
import pytest

from respx.utils import SetCookie, decode_data


@pytest.mark.parametrize(
    ("content_type", "value", "encoding"),
    [
        ("application/json", '{"language":"한국어"}', "utf-8"),
        ("application/xml", "<language>ko</language>", "utf-8"),
        (
            "application/json; charset=iso-8859-1",
            '{"language":"français"}',
            "iso-8859-1",
        ),
        ("application/json", "", "utf-8"),
        ("text/plain", "한국어", "utf-8"),
    ],
)
def test_decode_multipart_form_fields(content_type, value, encoding):
    request = httpx.Request(
        "POST",
        "https://example.org/upload",
        data={"request_id": "123"},
        files={
            "metadata": (None, value.encode(encoding), content_type),
            "audio": ("speech.wav", b"RIFF", "audio/wav"),
            "transcript": ("transcript.txt", b"hello", "text/plain"),
        },
    )

    data, files = decode_data(request)

    assert data.multi_items() == [("request_id", "123"), ("metadata", value)]
    assert files == {
        "audio": (("speech.wav", b"RIFF"),),
        "transcript": (("transcript.txt", b"hello"),),
    }


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
