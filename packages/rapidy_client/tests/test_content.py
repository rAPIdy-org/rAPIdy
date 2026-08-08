import zlib
from collections.abc import AsyncIterable
from pathlib import Path

import pytest
from rapidy_client._content import (
    CONTENT_DECODERS,
    CONTENT_ENCODERS,
    ContentFactory,
    FilePart,
    deflate_decode,
    deflate_encode,
    gzip_decode,
    gzip_encode,
)
from rapidy_client.errors import DecodeError


async def _collect(stream: AsyncIterable[bytes]) -> bytes:
    return b"".join([chunk async for chunk in stream])


@pytest.mark.asyncio
async def test_contentfactory_open_is_replayable() -> None:
    async def generate() -> AsyncIterable[bytes]:
        yield b"one"
        yield b"two"

    factory = ContentFactory(generate)
    first = factory.open()
    second = factory.open()
    assert isinstance(first, AsyncIterable)
    assert isinstance(second, AsyncIterable)
    assert first is not second
    assert await _collect(first) == await _collect(second) == b"onetwo"


def test_contentfactory_open_bytes() -> None:
    assert ContentFactory(lambda: b"body").open() == b"body"


def test_filepart_requires_exactly_one_source() -> None:
    with pytest.raises(ValueError):
        FilePart(name="f")
    with pytest.raises(ValueError):
        FilePart(name="f", path=Path("a"), content=b"x")


def test_filepart_filename_default_from_path() -> None:
    assert FilePart(name="f", path=Path("/tmp/report.pdf")).filename == "report.pdf"


def test_filepart_content_type_guess() -> None:
    assert FilePart(name="f", path=Path("a.json")).content_type == "application/json"
    assert FilePart(name="f", path=Path("a.unknown-extension")).content_type is None


def test_gzip_round_trip() -> None:
    payload = b"payload" * 10
    assert gzip_decode(gzip_encode(payload)) == payload


def test_deflate_round_trip_zlib() -> None:
    payload = b"payload" * 10
    assert deflate_decode(deflate_encode(payload)) == payload


def test_deflate_decode_accepts_raw() -> None:
    payload = b"payload" * 10
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    encoded = compressor.compress(payload) + compressor.flush()
    assert deflate_decode(encoded) == payload


def test_gzip_decode_bad_raises() -> None:
    with pytest.raises(DecodeError) as error:
        gzip_decode(b"not-gzip")
    assert error.value.__cause__ is not None


def test_deflate_decode_bad_raises() -> None:
    with pytest.raises(DecodeError):
        deflate_decode(b"\x00\x01garbage")


def test_codec_registries() -> None:
    assert set(CONTENT_ENCODERS) == set(CONTENT_DECODERS) == {"gzip", "deflate"}
