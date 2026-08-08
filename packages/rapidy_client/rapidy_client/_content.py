from __future__ import annotations

import gzip
import mimetypes
import zlib
from collections.abc import AsyncIterable, AsyncIterator, Callable, Mapping
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

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


def _optional_import(name: str) -> ModuleType | None:
    try:
        return import_module(name)
    except ImportError:
        return None


_brotli = _optional_import("brotli") or _optional_import("brotlicffi")
_zstd_stdlib = _optional_import("compression.zstd")
_zstandard = _optional_import("zstandard")

HAS_BROTLI = _brotli is not None
HAS_ZSTD = _zstd_stdlib is not None or _zstandard is not None
EXTRA_FOR_ENCODING: dict[str, str] = {"br": "brotli", "zstd": "zstd"}


def br_encode(data: bytes) -> bytes:
    if _brotli is None:
        raise DecodeError("brotli codec unavailable; install extra '[brotli]'")
    return cast("bytes", _brotli.compress(data))


def br_decode(data: bytes) -> bytes:
    if _brotli is None:
        raise DecodeError(
            "cannot decode Content-Encoding 'br'; install extra '[brotli]'"
        )
    try:
        return cast("bytes", _brotli.decompress(data))
    except Exception as exc:
        raise DecodeError("brotli content decode failed") from exc


def zstd_encode(data: bytes) -> bytes:
    if _zstd_stdlib is not None:
        return cast("bytes", _zstd_stdlib.compress(data))
    if _zstandard is not None:
        compressor = _zstandard.ZstdCompressor()
        return cast("bytes", compressor.compress(data))
    raise DecodeError("zstd codec unavailable; install extra '[zstd]'")


def zstd_decode(data: bytes) -> bytes:
    try:
        if _zstd_stdlib is not None:
            return cast("bytes", _zstd_stdlib.decompress(data))
        if _zstandard is not None:
            decompressor = _zstandard.ZstdDecompressor()
            return cast("bytes", decompressor.decompress(data))
    except Exception as exc:
        raise DecodeError("zstd content decode failed") from exc
    raise DecodeError(
        "cannot decode Content-Encoding 'zstd'; install extra '[zstd]'"
    )


if HAS_BROTLI:
    CONTENT_ENCODERS["br"] = br_encode
    CONTENT_DECODERS["br"] = br_decode
if HAS_ZSTD:
    CONTENT_ENCODERS["zstd"] = zstd_encode
    CONTENT_DECODERS["zstd"] = zstd_decode


def build_accept_encoding() -> str:
    tokens = ["gzip"]
    if HAS_BROTLI:
        tokens.append("br")
    if HAS_ZSTD:
        tokens.append("zstd")
    return ", ".join(tokens)


class _IncrementalDecoder(Protocol):
    @property
    def eof(self) -> bool: ...

    def decompress(self, data: bytes) -> bytes: ...

    def flush(self) -> bytes: ...


class _DeflateSniffDecoder:
    """Choose zlib-wrapped or raw deflate after seeing the first header."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._decoder: Any | None = None

    @property
    def eof(self) -> bool:
        return self._decoder is not None and bool(self._decoder.eof)

    def decompress(self, data: bytes) -> bytes:
        if self._decoder is not None:
            return cast("bytes", self._decoder.decompress(data))

        self._buffer.extend(data)
        if len(self._buffer) < 2:
            return b""

        buffered = bytes(self._buffer)
        self._buffer.clear()
        cmf, flg = buffered[:2]
        is_zlib_wrapped = (cmf & 0x0F) == 8 and ((cmf << 8) + flg) % 31 == 0
        wbits = zlib.MAX_WBITS if is_zlib_wrapped else -zlib.MAX_WBITS
        self._decoder = zlib.decompressobj(wbits)
        return self._decoder.decompress(buffered)

    def flush(self) -> bytes:
        if self._decoder is None:
            if not self._buffer:
                return b""
            buffered = bytes(self._buffer)
            self._buffer.clear()
            self._decoder = zlib.decompressobj(zlib.MAX_WBITS)
            return self._decoder.decompress(buffered) + self._decoder.flush()
        return cast("bytes", self._decoder.flush())


class _BrotliIncrementalDecoder:
    def __init__(self, module: ModuleType) -> None:
        self._decoder: Any = module.Decompressor()

    @property
    def eof(self) -> bool:
        return bool(self._decoder.is_finished())

    def decompress(self, data: bytes) -> bytes:
        return cast("bytes", self._decoder.process(data))

    def flush(self) -> bytes:
        return b""


class _ZstdIncrementalDecoder:
    def __init__(self, module: ModuleType, *, stdlib: bool) -> None:
        decompressor: Any = module.ZstdDecompressor()
        self._decoder: Any = decompressor if stdlib else decompressor.decompressobj()

    @property
    def eof(self) -> bool:
        return bool(getattr(self._decoder, "eof", True))

    def decompress(self, data: bytes) -> bytes:
        return cast("bytes", self._decoder.decompress(data))

    def flush(self) -> bytes:
        flush = getattr(self._decoder, "flush", None)
        return b"" if flush is None else cast("bytes", flush())


def _incremental_decoder(encoding: str) -> _IncrementalDecoder:
    if encoding == "gzip":
        return zlib.decompressobj(16 + zlib.MAX_WBITS)
    if encoding == "deflate":
        return _DeflateSniffDecoder()
    if encoding == "br" and _brotli is not None and "br" in CONTENT_DECODERS:
        return _BrotliIncrementalDecoder(_brotli)
    if encoding == "zstd" and "zstd" in CONTENT_DECODERS:
        if _zstd_stdlib is not None:
            return _ZstdIncrementalDecoder(_zstd_stdlib, stdlib=True)
        if _zstandard is not None:
            return _ZstdIncrementalDecoder(_zstandard, stdlib=False)

    extra = EXTRA_FOR_ENCODING.get(encoding, encoding)
    raise DecodeError(
        f"unsupported Content-Encoding {encoding!r}; install extra '[{extra}]'"
    )


async def decode_stream(
    encodings: list[str],
    source: AsyncIterable[bytes],
) -> AsyncIterator[bytes]:
    if not encodings:
        async for chunk in source:
            yield chunk
        return
    if len(encodings) > 1:
        raise DecodeError(
            f"chained Content-Encoding {encodings!r} unsupported "
            "(v1: single codec)"
        )

    encoding = encodings[0].strip().casefold()
    decoder = _incremental_decoder(encoding)
    try:
        async for chunk in source:
            decoded = decoder.decompress(chunk)
            if decoded:
                yield decoded
        tail = decoder.flush()
        if tail:
            yield tail
        if not decoder.eof:
            raise DecodeError(f"{encoding} content decode failed: incomplete stream")
    except DecodeError:
        raise
    except Exception as exc:
        raise DecodeError(f"{encoding} content decode failed") from exc

__all__ = (
    "CONTENT_DECODERS",
    "CONTENT_ENCODERS",
    "EXTRA_FOR_ENCODING",
    "HAS_BROTLI",
    "HAS_ZSTD",
    "ContentFactory",
    "FilePart",
    "br_decode",
    "br_encode",
    "build_accept_encoding",
    "decode_stream",
    "deflate_decode",
    "deflate_encode",
    "gzip_decode",
    "gzip_encode",
    "zstd_decode",
    "zstd_encode",
)
