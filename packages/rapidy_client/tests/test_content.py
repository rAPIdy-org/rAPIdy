import json
import zlib
from collections.abc import AsyncIterable, AsyncIterator, Callable
from pathlib import Path

import pytest
from rapidy_client import (
    UNSET,
    URL,
    BodyTooLargeError,
    Headers,
    RedirectConfig,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
    UpstreamConfig,
)
from rapidy_client._content import (
    CONTENT_DECODERS,
    CONTENT_ENCODERS,
    HAS_BROTLI,
    HAS_ZSTD,
    ContentFactory,
    FilePart,
    br_decode,
    br_encode,
    build_accept_encoding,
    decode_stream,
    deflate_decode,
    deflate_encode,
    gzip_decode,
    gzip_encode,
    zstd_decode,
    zstd_encode,
)
from rapidy_client.errors import DecodeError


async def _collect(stream: AsyncIterable[bytes]) -> bytes:
    return b"".join([chunk async for chunk in stream])


async def _stream(*chunks: bytes) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


def _response(body: bytes, *, max_response_size: int | None = None) -> Response:
    request = Request(
        method="GET",
        url=URL("https://example.test/x"),
        headers=Headers(),
        content=None,
        extensions=RequestExtensions(
            upstream="test",
            endpoint="/x",
            request_id=None,
            timeout=Timeout(),
            retry=None,
            idempotent=True,
            auth_override=UNSET,
            deadline=None,
            redirects=RedirectConfig(),
        ),
    )
    return Response(
        status=200,
        headers=Headers(),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=1),
        stream=_stream(body),
        max_response_size=max_response_size,
    )


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
    assert set(CONTENT_ENCODERS) == set(CONTENT_DECODERS)
    assert {"gzip", "deflate"} <= set(CONTENT_DECODERS)
    assert ("br" in CONTENT_DECODERS) is HAS_BROTLI
    assert ("zstd" in CONTENT_DECODERS) is HAS_ZSTD


@pytest.mark.asyncio
async def test_aiter_bytes_not_limited_by_max_response_size() -> None:
    response = _response(b"0123456789", max_response_size=4)
    assert await _collect(response.aiter_bytes()) == b"0123456789"


@pytest.mark.asyncio
@pytest.mark.parametrize("reader", ["text", "json"])
async def test_buffered_readers_enforce_max_response_size(reader: str) -> None:
    body = json.dumps({"value": "large"}).encode()
    response = _response(body, max_response_size=4)
    with pytest.raises(BodyTooLargeError):
        await getattr(response, reader)()


@pytest.mark.asyncio
async def test_aread_capped_truncates_error_body() -> None:
    response = _response(b"0123456789")
    assert await response._aread_capped(4) == b"0123"
    assert await response.aread() == b"0123"
    assert response._consumed is True


def test_default_error_body_limit() -> None:
    assert UpstreamConfig(base_url="https://example.test").error_body_limit == 65536


@pytest.mark.asyncio
async def test_decode_stream_gzip_incrementally() -> None:
    encoded = gzip_encode(b"hello world" * 20)
    source = _stream(*(encoded[index : index + 1] for index in range(len(encoded))))
    assert await _collect(decode_stream(["gzip"], source)) == b"hello world" * 20


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [False, True])
async def test_decode_stream_deflate_header_sniff(raw: bool) -> None:
    payload = b"deflate payload" * 20
    if raw:
        compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        encoded = compressor.compress(payload) + compressor.flush()
    else:
        encoded = deflate_encode(payload)
    source = _stream(*(encoded[index : index + 1] for index in range(len(encoded))))
    assert await _collect(decode_stream(["deflate"], source)) == payload


@pytest.mark.asyncio
async def test_decode_stream_passthrough_when_empty() -> None:
    assert await _collect(decode_stream([], _stream(b"a", b"b"))) == b"ab"


@pytest.mark.asyncio
async def test_decode_stream_unknown_raises_with_hint() -> None:
    with pytest.raises(DecodeError, match="made-up.*made-up"):
        await _collect(decode_stream(["made-up"], _stream(b"body")))


@pytest.mark.asyncio
async def test_decode_stream_chained_raises() -> None:
    with pytest.raises(DecodeError, match="chained"):
        await _collect(decode_stream(["gzip", "br"], _stream(b"body")))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("encoding", "extra"),
    [("br", "brotli"), ("zstd", "zstd")],
)
async def test_optional_codec_without_registry_entry_has_extra_hint(
    monkeypatch: pytest.MonkeyPatch,
    encoding: str,
    extra: str,
) -> None:
    monkeypatch.delitem(CONTENT_DECODERS, encoding, raising=False)
    with pytest.raises(DecodeError, match=rf"{encoding}.*\[{extra}\]"):
        await _collect(decode_stream([encoding], _stream(b"body")))


def test_build_accept_encoding_lists_available_codecs() -> None:
    value = build_accept_encoding()
    tokens = value.split(", ")
    assert tokens[0] == "gzip"
    assert "deflate" not in tokens
    assert ("br" in tokens) is HAS_BROTLI
    assert ("zstd" in tokens) is HAS_ZSTD


@pytest.mark.skipif(not HAS_BROTLI, reason="brotli extra is not installed")
def test_brotli_round_trip() -> None:
    assert br_decode(br_encode(b"brotli" * 20)) == b"brotli" * 20


@pytest.mark.skipif(not HAS_ZSTD, reason="zstd extra is not installed")
def test_zstd_round_trip() -> None:
    assert zstd_decode(zstd_encode(b"zstd" * 20)) == b"zstd" * 20


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("encoding", "encoder"),
    [
        pytest.param(
            "br",
            br_encode,
            marks=pytest.mark.skipif(
                not HAS_BROTLI,
                reason="brotli extra is not installed",
            ),
        ),
        pytest.param(
            "zstd",
            zstd_encode,
            marks=pytest.mark.skipif(
                not HAS_ZSTD,
                reason="zstd extra is not installed",
            ),
        ),
    ],
)
async def test_optional_decode_stream(
    encoding: str,
    encoder: Callable[[bytes], bytes],
) -> None:
    payload = b"optional codec stream" * 20
    encoded = encoder(payload)
    source = _stream(
        *(encoded[index : index + 2] for index in range(0, len(encoded), 2))
    )
    assert await _collect(decode_stream([encoding], source)) == payload


@pytest.mark.asyncio
async def test_decode_stream_bad_gzip_wraps_cause() -> None:
    with pytest.raises(DecodeError) as error:
        await _collect(decode_stream(["gzip"], _stream(b"not-gzip")))
    assert error.value.__cause__ is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("encoding", "encoded"),
    [
        ("gzip", gzip_encode(b"truncated")),
        pytest.param(
            "br",
            br_encode(b"truncated") if HAS_BROTLI else b"",
            marks=pytest.mark.skipif(
                not HAS_BROTLI,
                reason="brotli extra is not installed",
            ),
        ),
        pytest.param(
            "zstd",
            zstd_encode(b"truncated") if HAS_ZSTD else b"",
            marks=pytest.mark.skipif(
                not HAS_ZSTD,
                reason="zstd extra is not installed",
            ),
        ),
    ],
)
async def test_decode_stream_rejects_truncated_input(
    encoding: str,
    encoded: bytes,
) -> None:
    with pytest.raises(DecodeError, match="incomplete"):
        await _collect(decode_stream([encoding], _stream(encoded[:-1])))
