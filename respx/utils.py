import email
from email.message import Message
from typing import List, Tuple, cast
from urllib.parse import parse_qsl

import httpx


class MultiItems(dict):
    def get_list(self, key: str) -> List[str]:
        try:
            return [self[key]]
        except KeyError:  # pragma: no cover
            return []

    def multi_items(self) -> List[Tuple[str, str]]:
        return list(self.items())


def _parse_multipart_form_data(
    content: bytes, *, content_type: str, encoding: str
) -> Tuple[MultiItems, MultiItems]:
    form_data = b"\r\n".join(
        (
            b"MIME-Version: 1.0",
            b"Content-Type: " + content_type.encode(encoding),
            b"\r\n" + content,
        )
    )
    data = MultiItems()
    files = MultiItems()
    for payload in email.message_from_bytes(form_data).get_payload():
        payload = cast(Message, payload)
        name = payload.get_param("name", header="Content-Disposition")
        filename = payload.get_filename()
        content_type = payload.get_content_type()
        value = payload.get_payload(decode=True)
        assert isinstance(value, bytes)
        if content_type.startswith("text/") and filename is None:
            # Text field
            data[name] = value.decode(payload.get_content_charset() or "utf-8")
        else:
            # File field
            files[name] = filename, value

    return data, files


def _parse_urlencoded_data(content: bytes, *, encoding: str) -> MultiItems:
    return MultiItems(
        (key, value)
        for key, value in parse_qsl(content.decode(encoding), keep_blank_values=True)
    )


def decode_data(request: httpx.Request) -> Tuple[MultiItems, MultiItems]:
    content = request.read()
    content_type = request.headers.get("Content-Type", "")

    if content_type.startswith("multipart/form-data"):
        data, files = _parse_multipart_form_data(
            content,
            content_type=content_type,
            encoding=request.headers.encoding,
        )
    else:
        data = _parse_urlencoded_data(
            content,
            encoding=request.headers.encoding,
        )
        files = MultiItems()

    return data, files
