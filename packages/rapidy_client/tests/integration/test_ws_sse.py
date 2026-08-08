from __future__ import annotations

import asyncio
import base64
import hashlib
from collections.abc import AsyncIterator

import pytest
from rapidy_client import BackoffConfig, HttpClient, SSEReconnect, UpstreamConfig
from wsproto import ConnectionType
from wsproto.connection import Connection
from wsproto.events import BytesMessage, CloseConnection, Ping, TextMessage

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _headers(head: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in head.decode("latin-1").split("\r\n")[1:]:
        name, separator, value = line.partition(":")
        if separator:
            result[name.casefold()] = value.strip()
    return result


async def _running_server(
    handler: object,
) -> AsyncIterator[tuple[asyncio.AbstractServer, int]]:
    server = await asyncio.start_server(handler, "127.0.0.1", 0)  # type: ignore[arg-type]
    sockets = server.sockets
    assert sockets
    try:
        yield server, int(sockets[0].getsockname()[1])
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_real_httpx_websocket_upgrade_and_echo() -> None:
    async def handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            headers = _headers(head)
            accept = base64.b64encode(
                hashlib.sha1(
                    (headers["sec-websocket-key"] + _GUID).encode("ascii"),
                    usedforsecurity=False,
                ).digest()
            ).decode("ascii")
            writer.write(
                (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Connection: Upgrade\r\n"
                    "Upgrade: websocket\r\n"
                    f"Sec-WebSocket-Accept: {accept}\r\n"
                    "Sec-WebSocket-Protocol: echo.v1\r\n\r\n"
                ).encode("ascii")
            )
            await writer.drain()
            connection = Connection(ConnectionType.SERVER)
            while data := await reader.read(65536):
                connection.receive_data(data)
                for event in connection.events():
                    if isinstance(event, TextMessage):
                        writer.write(connection.send(TextMessage(data=event.data)))
                    elif isinstance(event, BytesMessage):
                        writer.write(connection.send(BytesMessage(data=event.data)))
                    elif isinstance(event, Ping):
                        writer.write(connection.send(event.response()))
                    elif isinstance(event, CloseConnection):
                        writer.write(connection.send(event.response()))
                        await writer.drain()
                        return
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async for _, port in _running_server(handler):
        async with (
            HttpClient.simple(f"http://127.0.0.1:{port}") as client,
            client.ws(
                "/echo",
                subprotocols=("echo.v1",),
            ) as session,
        ):
            await session.send_text("hello")
            message = await session.receive()
            assert message.text == "hello"
            assert session.subprotocol == "echo.v1"


@pytest.mark.asyncio
async def test_real_httpx_sse_reconnect_sends_checkpoint() -> None:
    requests: list[dict[str, str]] = []

    async def handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            headers = _headers(head)
            requests.append(headers)
            identifier = str(len(requests))
            body = f"id: {identifier}\ndata: {identifier}\n\n".encode()
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/event-stream\r\n"
                + f"Content-Length: {len(body)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + body
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async for _, port in _running_server(handler):
        client = HttpClient(
            UpstreamConfig.model_validate({"base_url": f"http://127.0.0.1:{port}"})
        )
        connection = client.sse(
            "/events",
            reconnect=SSEReconnect(
                backoff=BackoffConfig(base=0.0, cap=0.0, jitter="none"),
                max_attempts=2,
            ),
        )
        async with connection as stream:
            assert (await anext(stream)).id == "1"
            assert (await anext(stream)).id == "2"
        await client.aclose()

    assert requests[0].get("last-event-id") is None
    assert requests[1]["last-event-id"] == "1"
