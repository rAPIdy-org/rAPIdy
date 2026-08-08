from __future__ import annotations

import asyncio
import gc
import warnings
from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from rapidy_client import (
    ContentFactory,
    FilePart,
    Headers,
    HttpClient,
    Request,
    Response,
    ResponseExtensions,
    Timeout,
    UpstreamConfig,
    aiter_file,
    download_to,
    guess_extension,
)
from rapidy_client._content import encode_multipart
from rapidy_client.files import DEFAULT_CONTENT_TYPE, guess_content_type
from rapidy_client.testing import MockTransport


async def _collect(content: AsyncIterable[bytes]) -> bytes:
    return b"".join([chunk async for chunk in content])


def _client(
    mock: MockTransport,
    **config: Any,
) -> HttpClient:
    settings = UpstreamConfig.model_validate(
        {
            "base_url": "https://files.example.test",
            "log": {"level": "off"},
            **config,
        }
    )
    return HttpClient(settings, transport=mock)


def _stream_route(
    mock: MockTransport,
    path: str,
    chunks: tuple[bytes, ...],
    closed: list[bool],
) -> None:
    async def stream() -> AsyncIterator[bytes]:
        for chunk in chunks:
            yield chunk

    async def on_close() -> None:
        closed.append(True)

    async def handler(request: Request) -> Response:
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(elapsed=0.0, attempt=0),
            stream=stream(),
            on_close=on_close,
        )

    mock.route("GET", path).respond_with(handler)


def test_guess_content_type_and_extension() -> None:
    assert guess_content_type("report.pdf") == "application/pdf"
    assert guess_content_type(Path("data.json")) == "application/json"
    assert guess_content_type("noext") is None
    assert guess_extension("application/json") == ".json"
    assert guess_extension("application/pdf") == ".pdf"
    assert guess_extension("text/markdown; charset=utf-8") == ".md"
    assert guess_extension("application/x-unknown-xyz") is None


@pytest.mark.asyncio
async def test_aiter_file_chunks(tmp_path: Path) -> None:
    data = b"A" * 200_000
    path = tmp_path / "payload.bin"
    path.write_bytes(data)

    chunks = [chunk async for chunk in aiter_file(path)]

    assert b"".join(chunks) == data
    assert len(chunks) == 4
    assert max(map(len, chunks)) <= 65536


@pytest.mark.asyncio
async def test_aiter_file_rejects_invalid_chunk_size(tmp_path: Path) -> None:
    stream = aiter_file(tmp_path / "unused", chunk_size=0)
    with pytest.raises(ValueError, match="greater than zero"):
        await anext(stream)


@pytest.mark.asyncio
async def test_download_to_streams_and_closes(tmp_path: Path) -> None:
    mock = MockTransport()
    closed: list[bool] = []
    _stream_route(mock, "/report", (b"chunk0", b"chunk1", b"chunk2"), closed)
    client = _client(mock)

    destination = await download_to(client, "/report", tmp_path / "report.bin")

    assert destination.read_bytes() == b"chunk0chunk1chunk2"
    assert closed == [True]
    await client.aclose()


@pytest.mark.asyncio
async def test_download_to_closes_on_write_error(tmp_path: Path) -> None:
    mock = MockTransport()
    closed: list[bool] = []
    _stream_route(mock, "/report", (b"content",), closed)
    client = _client(mock)

    with pytest.raises(OSError):
        await download_to(client, "/report", tmp_path / "missing" / "report.bin")

    assert closed == [True]
    await client.aclose()


@pytest.mark.asyncio
async def test_stream_not_leaked_on_early_break() -> None:
    mock = MockTransport()
    closed: list[bool] = []
    _stream_route(mock, "/stream", (b"one", b"two"), closed)
    client = _client(mock)

    async with client.stream("GET", "/stream") as response:
        async for _ in response.aiter_bytes(3):
            break

    assert response._closed is True
    assert closed == [True]
    await client.aclose()


@pytest.mark.asyncio
async def test_context_closes_body_on_exception() -> None:
    mock = MockTransport()
    closed: list[bool] = []
    _stream_route(mock, "/stream", (b"one",), closed)
    client = _client(mock)

    with pytest.raises(RuntimeError, match="consumer failed"):
        async with client.stream("GET", "/stream"):
            raise RuntimeError("consumer failed")

    assert closed == [True]
    await client.aclose()


@pytest.mark.asyncio
async def test_gc_warning_in_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPIDY_CLIENT_DEBUG", "1")
    mock = MockTransport()
    closed: list[bool] = []
    _stream_route(mock, "/stream", (b"one",), closed)
    client = _client(mock)
    context = client.stream("GET", "/stream")
    response = await context.__aenter__()

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ResourceWarning)
        del context
        gc.collect()
        await asyncio_tick()

    assert any("unclosed HttpClient stream" in str(item.message) for item in captured)
    assert response._closed is True
    assert closed == [True]
    await client.aclose()


@pytest.mark.asyncio
async def test_no_gc_warning_outside_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAPIDY_CLIENT_DEBUG", raising=False)
    mock = MockTransport()
    closed: list[bool] = []
    _stream_route(mock, "/stream", (b"one",), closed)
    client = _client(mock)
    context = client.stream("GET", "/stream")
    response = await context.__aenter__()

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ResourceWarning)
        del context
        gc.collect()
        await asyncio_tick()

    assert not [item for item in captured if item.category is ResourceWarning]
    assert response._closed is True
    assert closed == [True]
    await client.aclose()


async def asyncio_tick() -> None:
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_multipart_path_content_and_data(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    path.write_bytes(b"PDF-CONTENT")
    content_type, factory = encode_multipart(
        [
            FilePart(name="file", path=path),
            FilePart(
                name="meta",
                content=b'{"kind":"report"}',
                content_type="application/json",
            ),
        ],
        {"title": "Q2"},
        boundary="fixed-boundary",
    )
    opened = factory.open()
    assert isinstance(opened, AsyncIterable)
    body = await _collect(opened)

    assert content_type == "multipart/form-data; boundary=fixed-boundary"
    assert b"--fixed-boundary\r\n" in body
    assert body.endswith(b"--fixed-boundary--\r\n")
    assert b'form-data; name="title"\r\n\r\nQ2' in body
    assert b'name="file"; filename="report.pdf"' in body
    assert b"Content-Type: application/pdf" in body
    assert b"PDF-CONTENT" in body
    assert b'name="meta"' in body
    assert b"Content-Type: application/json" in body
    assert b'{"kind":"report"}' in body


@pytest.mark.asyncio
async def test_multipart_default_type_escape_and_replay(tmp_path: Path) -> None:
    path = tmp_path / "unknown"
    path.write_bytes(b"first")
    _, factory = encode_multipart(
        [FilePart(name='a"b\r\n', path=path)],
        boundary="fixed",
    )

    first = factory.open()
    assert isinstance(first, AsyncIterable)
    first_body = await _collect(first)
    path.write_bytes(b"second")
    second = factory.open()
    assert isinstance(second, AsyncIterable)
    second_body = await _collect(second)

    assert f"Content-Type: {DEFAULT_CONTENT_TYPE}".encode() in first_body
    assert b'name="a%22b%0D%0A"' in first_body
    assert b"first" in first_body
    assert b"second" in second_body


@pytest.mark.asyncio
async def test_multipart_streams_large_path_in_bounded_chunks(tmp_path: Path) -> None:
    path = tmp_path / "large.bin"
    path.write_bytes(b"x" * (5 * 1024 * 1024))
    _, factory = encode_multipart(
        [FilePart(name="large", path=path)],
        boundary="fixed",
    )
    opened = factory.open()
    assert isinstance(opened, AsyncIterable)

    chunk_sizes = [len(chunk) async for chunk in opened]

    assert max(chunk_sizes) <= 65536


def test_multipart_request_and_body_source_rules(tmp_path: Path) -> None:
    path = tmp_path / "upload.bin"
    path.write_bytes(b"payload")
    client = _client(MockTransport())
    part = FilePart(name="file", path=path)

    request = client._build_request(
        "POST",
        "/docs",
        files=[part],
        data={"title": "report"},
    )

    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert isinstance(request.content, ContentFactory)
    assert request.is_replayable is True
    with pytest.raises(ValueError, match="body"):
        client._build_request("POST", "/docs", json={"x": 1}, files=[part])


def test_explicit_multipart_content_type_wins() -> None:
    client = _client(MockTransport())
    request = client._build_request(
        "POST",
        "/docs",
        headers={"Content-Type": "custom/multipart"},
        files=[FilePart(name="file", content=b"payload")],
    )
    assert request.headers["content-type"] == "custom/multipart"


def test_upload_replayable_guard(tmp_path: Path) -> None:
    path = tmp_path / "upload.bin"
    path.write_bytes(b"payload")
    client = _client(MockTransport())

    one_shot = client._build_request(
        "POST",
        "/blob",
        content=aiter_file(path),
    )
    replayable = client._build_request(
        "POST",
        "/blob",
        content=ContentFactory(lambda: aiter_file(path)),
    )
    buffered = client._build_request("POST", "/blob", content=b"payload")

    assert one_shot.is_replayable is False
    assert one_shot.extensions.retry is None
    assert replayable.is_replayable is True
    assert replayable.extensions.retry == client._config.retry
    assert buffered.extensions.retry == client._config.retry


@pytest.mark.asyncio
async def test_no_size_limit_on_stream() -> None:
    mock = MockTransport()
    closed: list[bool] = []
    chunks = (b"x" * 800, b"y" * 800)
    _stream_route(mock, "/large", chunks, closed)
    client = _client(mock, max_response_size=1024)

    async with client.stream("GET", "/large") as response:
        total = 0
        async for chunk in response.aiter_bytes(256):
            total += len(chunk)

    assert total == 1600
    assert closed == [True]
    await client.aclose()


@pytest.mark.asyncio
async def test_stream_timeout_defaults_and_override() -> None:
    mock = MockTransport()
    mock.route("GET", "/default").respond()
    mock.route("GET", "/explicit").respond()
    client = _client(mock)

    async with client.stream("GET", "/default"):
        pass
    async with client.stream("GET", "/explicit", timeout=5.0):
        pass

    assert mock.calls[0].request.extensions.timeout.total is None
    assert mock.calls[1].request.extensions.timeout == Timeout(total=5.0)
    await client.aclose()


def test_facade_reexports() -> None:
    assert callable(aiter_file)
    assert callable(download_to)
    assert guess_extension("application/json") == ".json"
