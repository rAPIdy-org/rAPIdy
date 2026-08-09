from __future__ import annotations

import asyncio
import base64
import hashlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

import pytest
from pydantic import BaseModel, TypeAdapter
from rapidy_client import (
    BackoffConfig,
    ClientClosedError,
    Headers,
    HttpClient,
    MessageValidationError,
    Request,
    Response,
    ResponseExtensions,
    SchemaDefinitionError,
    UpstreamConfig,
    WSHandshakeError,
    WSMessageTooLargeError,
    WSQueueFullError,
    WSSocket,
    bind,
    ws,
)
from rapidy_client.schema import Header, PathParam, QueryParam
from rapidy_client.ws import WSConnect
from wsproto import ConnectionType
from wsproto.connection import Connection
from wsproto.events import BytesMessage, CloseConnection, Ping, TextMessage

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


async def _empty_body() -> AsyncIterator[bytes]:
    if False:
        yield b""


class _EchoStream:
    def __init__(self) -> None:
        self._server = Connection(ConnectionType.SERVER)
        self._incoming: asyncio.Queue[bytes] = asyncio.Queue()
        self.read_count = 0
        self.closed = False

    async def read(self, max_bytes: int = 65536) -> bytes:
        del max_bytes
        self.read_count += 1
        return await self._incoming.get()

    async def push_text(self, data: str, *, message_finished: bool = True) -> None:
        await self._incoming.put(
            self._server.send(TextMessage(data=data, message_finished=message_finished))
        )

    async def write(self, data: bytes) -> None:
        self._server.receive_data(data)
        for event in self._server.events():
            if isinstance(event, TextMessage):
                await self._incoming.put(
                    self._server.send(TextMessage(data=event.data))
                )
            elif isinstance(event, BytesMessage):
                await self._incoming.put(
                    self._server.send(BytesMessage(data=event.data))
                )
            elif isinstance(event, (Ping, CloseConnection)):
                await self._incoming.put(self._server.send(event.response()))

    async def aclose(self) -> None:
        self.closed = True


class _BlockingStream(_EchoStream):
    def __init__(self) -> None:
        super().__init__()
        self.write_started = asyncio.Event()
        self.release_write = asyncio.Event()

    async def write(self, data: bytes) -> None:
        self.write_started.set()
        await self.release_write.wait()
        await super().write(data)


@dataclass(slots=True)
class _Upgrade:
    status: int
    headers: Headers
    network_stream: _EchoStream | None
    error_body: bytes = b""


class _WSTransport:
    def __init__(self, *, status: int = 101, bad_accept: bool = False) -> None:
        self.status = status
        self.bad_accept = bad_accept
        self.requests: list[Request] = []
        self.streams: list[_EchoStream] = []

    def _make_stream(self) -> _EchoStream:
        return _EchoStream()

    async def handle(self, request: Request) -> Response:
        return Response(
            status=200,
            headers=Headers(),
            request=request,
            extensions=ResponseExtensions(elapsed=0.0, attempt=1),
            stream=_empty_body(),
        )

    async def connect_ws(self, request: Request) -> _Upgrade:
        self.requests.append(request)
        if self.status != 101:
            return _Upgrade(self.status, Headers(), None, b"rejected")
        key = request.headers["Sec-WebSocket-Key"]
        accept = base64.b64encode(
            hashlib.sha1(
                (key + _GUID).encode(),
                usedforsecurity=False,
            ).digest()
        ).decode()
        stream = self._make_stream()
        self.streams.append(stream)
        return _Upgrade(
            101,
            Headers(
                {
                    "Sec-WebSocket-Accept": "bad" if self.bad_accept else accept,
                    "Sec-WebSocket-Protocol": "json.v1",
                }
            ),
            stream,
        )

    async def aclose(self) -> None:
        return None


class _BlockingWSTransport(_WSTransport):
    def _make_stream(self) -> _EchoStream:
        return _BlockingStream()


class _SafeMiddleware:
    handshake_safe: ClassVar[bool] = True

    def __init__(self) -> None:
        self.called = 0

    async def __call__(self, request: Request, call_next: Any) -> Response:
        self.called += 1
        return await call_next(request)


class _UnsafeMiddleware(_SafeMiddleware):
    handshake_safe: ClassVar[bool] = False


class Message(BaseModel):
    value: int


@ws("/echo", subprotocols=("json.v1",))
async def echo_socket() -> WSSocket[Message]:
    pass


@ws("/echo/{tenant}", subprotocols=("json.v1",))
async def marked_socket(
    tenant: Annotated[str, PathParam()],
    cursor: Annotated[int, QueryParam(alias="after")],
    token: Annotated[str, Header(alias="X-Token")],
) -> WSSocket[Message]:
    pass


def _client(
    transport: _WSTransport,
    *,
    middlewares: tuple[Any, ...] = (),
) -> HttpClient:
    return HttpClient(
        UpstreamConfig(
            base_url="https://example.test",
            default_headers={"Authorization": "Bearer token"},
        ),
        transport=transport,
        middlewares=middlewares,
    )


@pytest.mark.asyncio
async def test_declarative_typed_websocket_echo() -> None:
    transport = _WSTransport()
    endpoint = bind(echo_socket, _client(transport))

    handle = await endpoint()
    async with handle as socket:
        await socket.send(Message(value=42))
        assert await socket.receive() == Message(value=42)
        assert socket.subprotocol == "json.v1"

    assert transport.streams[0].closed


@pytest.mark.asyncio
async def test_reduced_handshake_chain_and_default_headers() -> None:
    safe = _SafeMiddleware()
    unsafe = _UnsafeMiddleware()
    transport = _WSTransport()
    client = _client(transport, middlewares=(safe, unsafe))

    async with client.ws("/echo", subprotocols=("json.v1",)):
        pass

    assert safe.called == 1
    assert unsafe.called == 0
    assert transport.requests[0].headers["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_declarative_markers_reach_websocket_handshake() -> None:
    transport = _WSTransport()
    endpoint = bind(marked_socket, _client(transport))

    async with await endpoint("acme", 7, "secret"):
        pass

    request = transport.requests[0]
    assert request.url.path == "/echo/acme"
    assert request.url.query_string == "after=7"
    assert request.headers["X-Token"] == "secret"


@pytest.mark.asyncio
async def test_handshake_rejection_and_bad_accept() -> None:
    with pytest.raises(WSHandshakeError) as rejected:
        await _client(_WSTransport(status=503)).ws("/echo").__aenter__()
    assert rejected.value.status == 503

    transport = _WSTransport(bad_accept=True)
    with pytest.raises(WSHandshakeError) as invalid:
        await _client(transport).ws("/echo", subprotocols=("json.v1",)).__aenter__()
    assert invalid.value.status == 101
    assert transport.streams[0].closed


@pytest.mark.asyncio
async def test_typed_receive_validation_error() -> None:
    transport = _WSTransport()
    connection = WSConnect[Message, Message](
        _client(transport),
        "/echo",
        subprotocols=("json.v1",),
        _send_adapter=TypeAdapter(Message),
        _recv_adapter=TypeAdapter(Message),
    )
    async with connection as session:
        await session.send_text('{"value":"not-an-int"}')
        with pytest.raises(MessageValidationError):
            await session.receive_typed()


@pytest.mark.asyncio
async def test_send_queue_timeout_and_single_receive_consumer() -> None:
    transport = _BlockingWSTransport()
    client = _client(transport)
    connection = client.ws(
        "/echo",
        subprotocols=("json.v1",),
        send_queue_limit=1,
        send_timeout=0.01,
    )
    session = await connection.__aenter__()
    stream = transport.streams[0]
    assert isinstance(stream, _BlockingStream)

    await session.send_text("one")
    await stream.write_started.wait()
    await session.send_text("two")
    with pytest.raises(WSQueueFullError):
        await session.send_text("three")

    receiving = asyncio.create_task(session.receive())
    await asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="active receive"):
        await session.receive()

    await client.aclose()
    with pytest.raises(ClientClosedError):
        await receiving


@pytest.mark.asyncio
async def test_receive_queue_backpressures_network_reader() -> None:
    transport = _WSTransport()
    connection = _client(transport).ws(
        "/echo",
        subprotocols=("json.v1",),
        receive_queue_limit=1,
    )

    async with connection as session:
        stream = transport.streams[0]
        await stream.push_text("one")
        await stream.push_text("two")
        await stream.push_text("three")
        for _ in range(20):
            await asyncio.sleep(0)
            if stream.read_count >= 2:
                break

        assert session._receive_queue.maxsize == 1
        assert session._receive_queue.qsize() == 1
        assert stream.read_count == 2
        assert (await session.receive()).text == "one"

        for _ in range(20):
            await asyncio.sleep(0)
            if stream.read_count >= 3:
                break
        assert stream.read_count == 3
        assert (await session.receive()).text == "two"
        assert (await session.receive()).text == "three"


@pytest.mark.asyncio
async def test_fragmented_message_size_limit_fails_and_closes_stream() -> None:
    transport = _WSTransport()
    connection = _client(transport).ws(
        "/echo",
        subprotocols=("json.v1",),
        max_message_size=5,
    )

    async with connection as session:
        stream = transport.streams[0]
        await stream.push_text("abc", message_finished=False)
        await stream.push_text("def")

        with pytest.raises(WSMessageTooLargeError, match="max_message_size=5") as error:
            await session.receive()

        assert error.value.endpoint == "/echo"
        assert stream.closed


def test_websocket_resource_limits_must_be_positive() -> None:
    client = _client(_WSTransport())
    with pytest.raises(ValueError, match="max_message_size"):
        client.ws("/echo", max_message_size=0)
    with pytest.raises(ValueError, match="receive_queue_limit"):
        client.ws("/echo", receive_queue_limit=0)


@pytest.mark.asyncio
async def test_reconnect_retries_5xx_but_not_4xx() -> None:
    class SequencedTransport(_WSTransport):
        def __init__(self, statuses: list[int]) -> None:
            super().__init__()
            self.statuses = statuses

        async def connect_ws(self, request: Request) -> _Upgrade:
            self.status = self.statuses.pop(0)
            return await super().connect_ws(request)

    rejected = _client(SequencedTransport([403])).ws("/echo")
    with pytest.raises(WSHandshakeError) as error:
        await anext(rejected.reconnect(max_attempts=2))
    assert error.value.status == 403

    retried_transport = SequencedTransport([503, 101])
    retried = _client(retried_transport).ws(
        "/echo",
        subprotocols=("json.v1",),
    )
    iterator = retried.reconnect(
        backoff=BackoffConfig(base=0.0, cap=0.0),
        max_attempts=2,
    )
    session = await anext(iterator)
    assert session.subprotocol == "json.v1"
    assert len(retried_transport.requests) == 2
    await iterator.aclose()


def test_ws_declaration_rejects_wrong_return_type_at_bind() -> None:
    @ws("/bad")
    async def bad() -> Message:
        pass

    with pytest.raises(SchemaDefinitionError, match="must return"):
        bind(bad, _client(_WSTransport()))
