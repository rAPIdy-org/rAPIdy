from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from http.cookies import SimpleCookie
from tempfile import SpooledTemporaryFile
from types import MappingProxyType
from typing import Any, BinaryIO, NamedTuple
from urllib.parse import parse_qsl

from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header

from spikes._mini.request_proto import Request
from spikes.spike_b_extraction.mimetype_proto import (
    content_type_matches,
    parse_mimetype,
)


class RequestEntityTooLarge(Exception):
    pass


class IncorrectContentTypeError(Exception):
    def __init__(self, *, error: str) -> None:
        self.error = error
        super().__init__(error)


class FileField(NamedTuple):
    name: str
    filename: str
    file: BinaryIO
    content_type: str
    headers: CIMultiDictProxy[str]


class RequestProto(Request):
    def __init__(
        self, scope: dict[str, Any], receive: Any, *, client_max_size: int = 1024**2
    ) -> None:
        super().__init__(scope, receive)
        self.client_max_size = client_max_size
        self._read_bytes: bytes | None = None
        self._read_lock = asyncio.Lock()
        self._post: MultiDictProxy[str | bytes | FileField] | None = None

    @property
    def query(self) -> MultiDictProxy[str]:
        pairs = parse_qsl(
            self.scope.get("query_string", b"").decode(), keep_blank_values=True
        )
        return MultiDictProxy(MultiDict(pairs))

    @property
    def cookies(self) -> Mapping[str, str]:
        parsed: SimpleCookie[str] = SimpleCookie()
        parsed.load(self.headers.get("cookie", ""))
        return MappingProxyType({name: morsel.value for name, morsel in parsed.items()})

    @property
    def content_type(self) -> str:
        return parse_mimetype(self.headers.get("content-type", "")).type + (
            f"/{parse_mimetype(self.headers.get('content-type', '')).subtype}"
            if parse_mimetype(self.headers.get("content-type", "")).subtype
            else ""
        )

    async def read(self) -> bytes:
        if self._read_bytes is not None:
            return self._read_bytes
        async with self._read_lock:
            if self._read_bytes is not None:
                return self._read_bytes
            body = bytearray()
            while True:
                message = await self.receive()
                if message["type"] == "http.disconnect":
                    raise ConnectionResetError
                if message["type"] != "http.request":
                    continue
                body.extend(message.get("body", b""))
                if self.client_max_size > 0 and len(body) > self.client_max_size:
                    raise RequestEntityTooLarge((self.client_max_size, len(body)))
                if not message.get("more_body", False):
                    break
            self._read_bytes = bytes(body)
            return self._read_bytes

    async def json(self) -> Any:
        return json.loads((await self.read()).decode("utf-8"))

    async def post(self) -> MultiDictProxy[str | bytes | FileField]:
        if self._post is not None:
            return self._post
        content_type_header = self.headers.get("content-type", "")
        mime = parse_mimetype(content_type_header)
        output: MultiDict[str | bytes | FileField] = MultiDict()
        body = await self.read()
        if mime.type == "application" and mime.subtype == "x-www-form-urlencoded":
            charset = mime.parameters.get("charset", "utf-8")
            output.extend(parse_qsl(body.decode(charset), keep_blank_values=True))
        elif mime.type == "multipart" and mime.subtype == "form-data":
            boundary = mime.parameters.get("boundary")
            if not boundary:
                raise ValueError("Multipart boundary is missing.")
            _parse_multipart(body, boundary.encode(), output)
        self._post = MultiDictProxy(output)
        return self._post


def _parse_multipart(
    body: bytes,
    boundary: bytes,
    output: MultiDict[str | bytes | FileField],
) -> None:
    part_headers: CIMultiDict[str]
    header_name = bytearray()
    header_value = bytearray()
    part_data = bytearray()

    def on_part_begin() -> None:
        nonlocal part_headers
        part_headers = CIMultiDict()
        header_name.clear()
        header_value.clear()
        part_data.clear()

    def on_header_field(data: bytes, start: int, end: int) -> None:
        header_name.extend(data[start:end])

    def on_header_value(data: bytes, start: int, end: int) -> None:
        header_value.extend(data[start:end])

    def on_header_end() -> None:
        part_headers.add(header_name.decode("latin-1"), header_value.decode("latin-1"))
        header_name.clear()
        header_value.clear()

    def on_part_data(data: bytes, start: int, end: int) -> None:
        part_data.extend(data[start:end])

    def on_part_end() -> None:
        disposition = part_headers.get("content-disposition", "").encode("latin-1")
        _, options = parse_options_header(disposition)
        raw_name = options.get(b"name")
        if raw_name is None:
            raise ValueError("Multipart field missing name.")
        name = raw_name.decode("utf-8")
        raw_filename = options.get(b"filename")
        content_type = part_headers.get("content-type", "application/octet-stream")
        if raw_filename is not None:
            file = SpooledTemporaryFile(max_size=1024**2, mode="w+b")
            file.write(part_data)
            file.seek(0)
            output.add(
                name,
                FileField(
                    name,
                    raw_filename.decode("utf-8"),
                    file,
                    content_type,
                    CIMultiDictProxy(part_headers.copy()),
                ),
            )
            return
        if content_type.startswith("text/") or "content-type" not in part_headers:
            charset = parse_mimetype(content_type).parameters.get("charset", "utf-8")
            output.add(name, bytes(part_data).decode(charset))
        else:
            output.add(name, bytes(part_data))

    parser = MultipartParser(
        boundary,
        {
            "on_part_begin": on_part_begin,
            "on_header_field": on_header_field,
            "on_header_value": on_header_value,
            "on_header_end": on_header_end,
            "on_part_data": on_part_data,
            "on_part_end": on_part_end,
        },
    )
    parser.write(body)
    parser.finalize()


async def extract_all_sources(request: RequestProto) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    ensure_content_type(content_type, "application/*")
    return {
        "body": await request.json(),
        "header": request.headers.get("x-token"),
        "cookie": request.cookies.get("session"),
        "path": request.path_params.get("item_id"),
        "query": request.query.get("q"),
    }


def ensure_content_type(actual: str, expected: str) -> None:
    if content_type_matches(actual, expected):
        return
    actual_mime = parse_mimetype(actual)
    expected_mime = parse_mimetype(expected)
    if not actual_mime.type and not actual_mime.subtype:
        error = (
            "`Content-Type` header cannot be empty. "
            f"Expected: `{expected_mime.type}/{expected_mime.subtype}`"
        )
    else:
        error = (
            f"Expected Content-Type `{expected_mime.type}/{expected_mime.subtype}` "
            f"not `{actual_mime.type}/{actual_mime.subtype}`"
        )
    raise IncorrectContentTypeError(error=error)


__all__ = (
    "FileField",
    "IncorrectContentTypeError",
    "RequestEntityTooLarge",
    "RequestProto",
    "ensure_content_type",
    "extract_all_sources",
)
