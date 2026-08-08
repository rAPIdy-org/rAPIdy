import asyncio
import time

import pytest
from rapidy_client.testing.chaos import ChaosServer

_REQUEST = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"


async def _read_response(
    reader: asyncio.StreamReader,
) -> tuple[bytes, bytes]:
    head = await reader.readuntil(b"\r\n\r\n")
    content_length = 0
    for line in head.split(b"\r\n"):
        name, separator, value = line.partition(b":")
        if separator and name.strip().lower() == b"content-length":
            content_length = int(value.strip())
            break
    body = await reader.readexactly(content_length)
    return head, body


async def _connect(
    server: ChaosServer,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    return await asyncio.open_connection(server.host, server.port)


@pytest.mark.asyncio
async def test_url_reflects_bound_port() -> None:
    async with ChaosServer() as server:
        assert server.port > 0
        assert server.url == f"http://127.0.0.1:{server.port}"


@pytest.mark.asyncio
async def test_start_stop_idempotent() -> None:
    server = ChaosServer()
    await server.start()
    await server.start()
    assert server.port > 0
    await server.stop()
    await server.stop()


@pytest.mark.asyncio
async def test_respond_ok_keepalive() -> None:
    async with ChaosServer() as server:
        reader, writer = await _connect(server)
        try:
            writer.write(_REQUEST)
            await writer.drain()
            first_head, first_body = await _read_response(reader)
            writer.write(_REQUEST)
            await writer.drain()
            second_head, second_body = await _read_response(reader)
        finally:
            writer.close()
            await writer.wait_closed()
    assert first_head.startswith(b"HTTP/1.1 200 OK")
    assert b"Connection: keep-alive" in first_head
    assert second_head.startswith(b"HTTP/1.1 200 OK")
    assert first_body == second_body == b""


@pytest.mark.asyncio
async def test_freeze_holds_without_bytes() -> None:
    async with ChaosServer().freeze(0.15) as server:
        reader, writer = await _connect(server)
        writer.write(_REQUEST)
        await writer.drain()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(reader.read(1), timeout=0.03)
        assert await asyncio.wait_for(reader.read(1), timeout=0.3) == b""
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_disconnect_after_n_bytes() -> None:
    async with ChaosServer().disconnect_after(10) as server:
        reader, writer = await _connect(server)
        writer.write(_REQUEST)
        await writer.drain()
        head = await reader.readuntil(b"\r\n\r\n")
        body = await reader.read()
        writer.close()
        await writer.wait_closed()
    assert b"Content-Length: 11" in head
    assert body == b"x" * 10


@pytest.mark.asyncio
async def test_reset_on_reuse() -> None:
    async with ChaosServer().reset_on_reuse() as server:
        reader, writer = await _connect(server)
        writer.write(_REQUEST)
        await writer.drain()
        await _read_response(reader)
        writer.write(_REQUEST)
        await writer.drain()
        try:
            second = await reader.read(1)
        except ConnectionResetError:
            second = b""
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionResetError:
            pass
    assert second == b""


@pytest.mark.asyncio
async def test_slow_body_rate() -> None:
    async with ChaosServer().slow_body(100) as server:
        reader, writer = await _connect(server)
        started = time.monotonic()
        writer.write(_REQUEST)
        await writer.drain()
        _, body = await _read_response(reader)
        elapsed = time.monotonic() - started
        writer.close()
        await writer.wait_closed()
    assert body == b"x" * 100
    assert elapsed >= 0.75


@pytest.mark.asyncio
async def test_retry_after_header() -> None:
    async with ChaosServer().retry_after("2", status=503) as server:
        reader, writer = await _connect(server)
        writer.write(_REQUEST)
        await writer.drain()
        head, body = await _read_response(reader)
        writer.close()
        await writer.wait_closed()
    assert head.startswith(b"HTTP/1.1 503 Service Unavailable")
    assert b"Retry-After: 2" in head
    assert body == b"retry later"


@pytest.mark.asyncio
async def test_stall_request_read_blocks_write() -> None:
    async with ChaosServer().stall_request_read(0.12) as server:
        reader, writer = await _connect(server)
        writer.write(
            b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1000000\r\n\r\n"
        )
        await writer.drain()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(reader.read(1), timeout=0.03)
        assert await asyncio.wait_for(reader.read(1), timeout=0.3) == b""
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_ws_drop_every() -> None:
    async with ChaosServer().ws_drop_every(2) as server:
        reader, writer = await _connect(server)
        writer.write(_REQUEST)
        await writer.drain()
        await _read_response(reader)
        writer.write(_REQUEST)
        await writer.drain()
        try:
            result = await reader.read(1)
        except ConnectionResetError:
            result = b""
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionResetError:
            pass
    assert result == b""
