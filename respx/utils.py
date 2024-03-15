import email
from email.message import Message
from typing import Any, List, Tuple, cast
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
) -> Tuple[MultiItems, List[Any]]:
    form_data = b"\r\n".join(
        (
            b"MIME-Version: 1.0",
            b"Content-Type: " + content_type.encode(encoding),
            b"\r\n" + content,
        )
    )
    data = MultiItems()
    files: List[Any] = []
    for payload in email.message_from_bytes(form_data).get_payload():
        payload = cast(Message, payload)
        filename = payload.get_filename()
        if payload.get_content_maintype() == "text" and filename is None:
            # Text field
            key = payload.get_param("name", header="Content-Disposition")
            value = payload.get_payload(decode=True)
            assert isinstance(value, bytes)
            data[key] = value.decode(payload.get_content_charset() or "utf-8")
        else:
            # TODO: Implement parsing file fields
            continue  # pragma: no cover

    return data, files


def _parse_urlencoded_data(content: bytes, *, encoding: str) -> MultiItems:
    return MultiItems(
        (key, value)
        for key, value in parse_qsl(content.decode(encoding), keep_blank_values=True)
    )


def decode_data(request: httpx.Request) -> Tuple[MultiItems, List]:
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
        files = []

    return data, files
