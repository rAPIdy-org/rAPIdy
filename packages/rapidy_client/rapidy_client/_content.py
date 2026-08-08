from __future__ import annotations

import gzip
import mimetypes
import zlib
from collections.abc import AsyncIterable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from rapidy_client.errors import DecodeError


class ContentFactory:
    __slots__ = ("_factory",)

    def __init__(self, factory: Callable[[], AsyncIterable[bytes] | bytes]) -> None:
        self._factory = factory

    def open(self) -> AsyncIterable[bytes] | bytes:
        return self._factory()


@dataclass(slots=True, kw_only=True)
class FilePart:
    name: str
    path: Path | None = None
    content: bytes | None = None
    filename: str | None = None
    content_type: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (self.path is None) == (self.content is None):
            raise ValueError("exactly one of path or content must be provided")
        if self.filename is None and self.path is not None:
            self.filename = self.path.name
        if self.content_type is None and self.filename is not None:
            self.content_type = mimetypes.guess_type(self.filename)[0]


def gzip_encode(data: bytes) -> bytes:
    return gzip.compress(data)


def gzip_decode(data: bytes) -> bytes:
    try:
        return gzip.decompress(data)
    except (OSError, EOFError) as exc:
        raise DecodeError("gzip content decode failed") from exc


def deflate_encode(data: bytes) -> bytes:
    return zlib.compress(data)


def deflate_decode(data: bytes) -> bytes:
    try:
        return zlib.decompress(data)
    except zlib.error:
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error as raw_error:
            raise DecodeError("deflate content decode failed") from raw_error


CONTENT_ENCODERS: dict[str, Callable[[bytes], bytes]] = {
    "gzip": gzip_encode,
    "deflate": deflate_encode,
}
CONTENT_DECODERS: dict[str, Callable[[bytes], bytes]] = {
    "gzip": gzip_decode,
    "deflate": deflate_decode,
}

__all__ = (
    "CONTENT_DECODERS",
    "CONTENT_ENCODERS",
    "ContentFactory",
    "FilePart",
    "deflate_decode",
    "deflate_encode",
    "gzip_decode",
    "gzip_encode",
)
