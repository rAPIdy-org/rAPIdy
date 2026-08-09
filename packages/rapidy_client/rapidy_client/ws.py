from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import logging
import os
import random
import sys
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any, Generic, Literal, Protocol, TypeVar, cast

from pydantic import TypeAdapter, ValidationError
from wsproto import ConnectionType
from wsproto.connection import Connection as _WSFrameConnection
from wsproto.events import (
    BytesMessage as _BytesMessage,
)
from wsproto.events import (
    CloseConnection as _CloseConnection,
)
from wsproto.events import (
    Ping as _Ping,
)
from wsproto.events import (
    Pong as _Pong,
)
from wsproto.events import (
    TextMessage as _TextMessage,
)

from rapidy_client._models import (
    CallNext,
    Headers,
    Middleware,
    QueryValue,
    Request,
    Response,
    ResponseExtensions,
)
from rapidy_client.config import BackoffConfig
from rapidy_client.errors import (
    ClientClosedError,
    HttpClientError,
    MessageValidationError,
    ProtocolError,
    WSClosedError,
    WSHandshakeError,
    WSMessageTooLargeError,
    WSQueueFullError,
)
from rapidy_client.middleware.deadline import DeadlineMiddleware

if TYPE_CHECKING:
    from pydantic import BaseModel

    from rapidy_client._client import HttpClient

TSend = TypeVar("TSend", bound="BaseModel")
TRecv = TypeVar("TRecv", bound="BaseModel")
TMsg = TypeVar("TMsg", bound="BaseModel")

__all__ = ["Heartbeat", "WSConnect", "WSMessage", "WSSession", "WSSocket"]

_LOGGER = logging.getLogger("rapidy_client.ws")
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_RNG = random.Random()


@dataclass(slots=True, kw_only=True)
class Heartbeat:
    interval: float = 20.0
    timeout: float = 20.0

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError("heartbeat interval must be greater than zero")
        if self.timeout <= 0:
            raise ValueError("heartbeat timeout must be greater than zero")


@dataclass(slots=True, kw_only=True)
class WSMessage:
    kind: Literal["text", "binary"]
    text: str | None
    data: bytes | None


class _WSNetworkStreamProto(Protocol):
    async def read(self, max_bytes: int = 65536) -> bytes: ...

    async def write(self, data: bytes) -> None: ...

    async def aclose(self) -> None: ...


class _WSUpgradeResultProto(Protocol):
    status: int
    headers: Headers
    network_stream: _WSNetworkStreamProto | None
    error_body: bytes


class _WSCapableTransport(Protocol):
    async def connect_ws(self, request: Request) -> _WSUpgradeResultProto: ...


class _ReceiveFailure:
    __slots__ = ()


class _CloseItem:
    __slots__ = ("code",)

    def __init__(self, code: int) -> None:
        self.code = code


_RECEIVE_FAILURE = _ReceiveFailure()


def _error_context(request: Request) -> dict[str, str | None]:
    return {
        "upstream": request.extensions.upstream,
        "endpoint": request.extensions.endpoint,
        "request_id": request.extensions.request_id,
    }


def _compose(middleware: Middleware, next_handler: CallNext) -> CallNext:
    async def handler(request: Request) -> Response:
        return await middleware(request, next_handler)

    return handler


def _full_jitter(backoff: BackoffConfig, exponent: int) -> float:
    ceiling = min(backoff.cap, backoff.base * (2**exponent))
    return _RNG.uniform(0.0, ceiling) if backoff.jitter == "full" else ceiling


class WSConnect(Generic[TSend, TRecv]):
    """A lazy WebSocket connection or an explicit reconnect iterator."""

    def __init__(
        self,
        client: HttpClient,
        path: str,
        *,
        heartbeat: Heartbeat | None = None,
        max_message_size: int = 16_777_216,
        receive_queue_limit: int = 256,
        send_queue_limit: int = 256,
        send_timeout: float = 10.0,
        subprotocols: Sequence[str] = (),
        headers: dict[str, str] | None = None,
        _send_adapter: TypeAdapter[Any] | None = None,
        _recv_adapter: TypeAdapter[Any] | None = None,
        _path_params: dict[str, object] | None = None,
        _query: dict[str, QueryValue] | None = None,
    ) -> None:
        if max_message_size <= 0:
            raise ValueError("max_message_size must be greater than zero")
        if receive_queue_limit <= 0:
            raise ValueError("receive_queue_limit must be greater than zero")
        if send_queue_limit <= 0:
            raise ValueError("send_queue_limit must be greater than zero")
        if send_timeout < 0:
            raise ValueError("send_timeout must be non-negative")
        if any(not protocol or "," in protocol for protocol in subprotocols):
            raise ValueError("WebSocket subprotocols must be non-empty tokens")
        self._client = client
        self._path = path
        self._heartbeat = heartbeat or Heartbeat()
        self._max_message_size = max_message_size
        self._receive_queue_limit = receive_queue_limit
        self._send_queue_limit = send_queue_limit
        self._send_timeout = send_timeout
        self._subprotocols = tuple(subprotocols)
        self._headers = dict(headers or {})
        self._send_adapter = _send_adapter
        self._recv_adapter = _recv_adapter
        self._path_params = _path_params
        self._query = _query
        self._session: WSSession[TSend, TRecv] | None = None

    async def _handshake(self) -> WSSession[TSend, TRecv]:
        client = self._client
        client._bind_loop()
        if client._closing:
            raise ClientClosedError("HttpClient is closed")

        websocket_key = base64.b64encode(os.urandom(16)).decode("ascii")
        headers = {
            "Connection": "Upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Key": websocket_key,
            **self._headers,
        }
        if self._subprotocols:
            headers["Sec-WebSocket-Protocol"] = ", ".join(self._subprotocols)
        request = client._build_request(
            "GET",
            self._path,
            path_params=self._path_params,
            query=self._query,
            headers=headers,
        )

        captured: dict[str, _WSUpgradeResultProto] = {}

        async def terminal(current: Request) -> Response:
            transport = cast("_WSCapableTransport", client._transport)
            result = await transport.connect_ws(current)
            captured["result"] = result
            return Response(
                status=result.status,
                headers=result.headers,
                request=current,
                extensions=ResponseExtensions(elapsed=0.0, attempt=1),
            )

        entry: CallNext = terminal
        middleware: list[Middleware] = [
            item
            for item in client._middlewares
            if bool(getattr(item, "handshake_safe", False))
        ]
        middleware.append(
            DeadlineMiddleware(client._config.deadline, clock=client._clock)
        )
        for item in reversed(middleware):
            entry = _compose(item, entry)
        await entry(request)

        result = captured.get("result")
        if result is None:
            raise WSHandshakeError(
                "WebSocket handshake middleware did not reach the transport",
                status=None,
                **_error_context(request),
            )
        stream = result.network_stream
        if result.status != 101 or stream is None:
            if stream is not None:
                await stream.aclose()
            raise WSHandshakeError(
                f"WebSocket handshake rejected with status {result.status}",
                status=result.status,
                **_error_context(request),
            )

        expected_accept = base64.b64encode(
            hashlib.sha1(
                (websocket_key + _WS_GUID).encode("ascii"),
                usedforsecurity=False,
            ).digest()
        ).decode("ascii")
        if result.headers.get("sec-websocket-accept") != expected_accept:
            await stream.aclose()
            raise WSHandshakeError(
                "WebSocket Sec-WebSocket-Accept mismatch",
                status=101,
                **_error_context(request),
            )
        selected = result.headers.get("sec-websocket-protocol")
        if selected is not None and selected not in self._subprotocols:
            await stream.aclose()
            raise WSHandshakeError(
                "server selected an unoffered WebSocket subprotocol",
                status=101,
                **_error_context(request),
            )

        session = WSSession[TSend, TRecv](
            _stream=stream,
            _client=client,
            _request=request,
            _heartbeat=self._heartbeat,
            _max_message_size=self._max_message_size,
            _receive_queue_limit=self._receive_queue_limit,
            _send_queue_limit=self._send_queue_limit,
            _send_timeout=self._send_timeout,
            _subprotocol=selected,
            _send_adapter=self._send_adapter,
            _recv_adapter=self._recv_adapter,
        )
        await session._start()
        client._infinite.add(session)
        return session

    async def __aenter__(self) -> WSSession[TSend, TRecv]:
        if self._session is not None:
            raise RuntimeError("WebSocket context manager cannot be entered twice")
        self._session = await self._handshake()
        return self._session

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        del exc_type, exc, tb
        if self._session is not None:
            await self._session.close()

    async def _reconnect(
        self,
        *,
        backoff: BackoffConfig,
        max_attempts: int | None,
    ) -> AsyncIterator[WSSession[TSend, TRecv]]:
        attempt = 0
        while not self._client._closing:
            try:
                session = await self._handshake()
            except WSHandshakeError as exc:
                if exc.status is None or exc.status < 500:
                    raise
                attempt += 1
                if max_attempts is not None and attempt >= max_attempts:
                    raise
                await self._client._clock.sleep(_full_jitter(backoff, attempt - 1))
                continue
            except HttpClientError as exc:
                if isinstance(exc, ClientClosedError):
                    return
                attempt += 1
                if max_attempts is not None and attempt >= max_attempts:
                    raise
                await self._client._clock.sleep(_full_jitter(backoff, attempt - 1))
                continue

            attempt = 0
            try:
                yield session
            finally:
                await session.close()

    def reconnect(
        self,
        *,
        backoff: BackoffConfig | None = None,
        max_attempts: int | None = None,
    ) -> AsyncIterator[WSSession[TSend, TRecv]]:
        if max_attempts is not None and max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero or None")
        effective = backoff or BackoffConfig(base=1.0, cap=60.0)
        return self._reconnect(backoff=effective, max_attempts=max_attempts)


class WSSession(Generic[TSend, TRecv]):
    """One live WebSocket session with a serialized bounded send queue."""

    def __init__(
        self,
        *,
        _stream: _WSNetworkStreamProto,
        _client: HttpClient,
        _request: Request,
        _heartbeat: Heartbeat,
        _max_message_size: int,
        _receive_queue_limit: int,
        _send_queue_limit: int,
        _send_timeout: float,
        _subprotocol: str | None,
        _send_adapter: TypeAdapter[Any] | None = None,
        _recv_adapter: TypeAdapter[Any] | None = None,
    ) -> None:
        self._stream = _stream
        self._client = _client
        self._request = _request
        self._heartbeat = _heartbeat
        self._max_message_size = _max_message_size
        self._send_timeout = _send_timeout
        self._subprotocol = _subprotocol
        self._send_adapter = _send_adapter
        self._recv_adapter = _recv_adapter
        self._connection = _WSFrameConnection(ConnectionType.CLIENT)
        self._receive_queue: asyncio.Queue[WSMessage | _ReceiveFailure] = asyncio.Queue(
            maxsize=_receive_queue_limit
        )
        self._send_queue: asyncio.Queue[bytes | _CloseItem] = asyncio.Queue(
            maxsize=_send_queue_limit
        )
        self._reader_task: asyncio.Task[None] | None = None
        self._writer_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._last_pong_at = 0.0
        self._consumer_active = False
        self._closed = False
        self._stream_closed = False
        self._close_exc: BaseException | None = None
        self._text_fragments: list[str] = []
        self._binary_fragments: list[bytes] = []
        self._message_size = 0

    @property
    def subprotocol(self) -> str | None:
        return self._subprotocol

    async def _start(self) -> None:
        self._last_pong_at = self._client._clock.monotonic()
        self._reader_task = asyncio.create_task(self._read_loop())
        self._writer_task = asyncio.create_task(self._write_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def _fail(self, exc: BaseException) -> None:
        if self._closed:
            return
        self._closed = True
        self._close_exc = exc
        with contextlib.suppress(asyncio.QueueFull):
            self._receive_queue.put_nowait(_RECEIVE_FAILURE)
        self._client._infinite.discard(self)

    def _message_event(self, event: _TextMessage | _BytesMessage) -> WSMessage | None:
        fragment_size = (
            len(event.data.encode("utf-8"))
            if isinstance(event, _TextMessage)
            else len(cast("bytes", event.data))
        )
        self._message_size += fragment_size
        if self._message_size > self._max_message_size:
            received = self._message_size
            self._message_size = 0
            self._text_fragments.clear()
            self._binary_fragments.clear()
            raise WSMessageTooLargeError(
                f"WebSocket message exceeded max_message_size={self._max_message_size} "
                f"bytes (received at least {received})",
                **_error_context(self._request),
            )
        if isinstance(event, _TextMessage):
            self._text_fragments.append(event.data)
            if event.message_finished:
                text = "".join(self._text_fragments)
                self._text_fragments.clear()
                self._message_size = 0
                return WSMessage(kind="text", text=text, data=None)
            return None

        self._binary_fragments.append(cast("bytes", event.data))
        if event.message_finished:
            data = b"".join(self._binary_fragments)
            self._binary_fragments.clear()
            self._message_size = 0
            return WSMessage(kind="binary", text=None, data=data)
        return None

    async def _read_loop(self) -> None:
        try:
            while not self._closed:
                data = await self._stream.read(65536)
                if not data:
                    self._fail(
                        WSClosedError(
                            "WebSocket peer closed the connection",
                            code=None,
                            reason=None,
                            **_error_context(self._request),
                        )
                    )
                    return
                self._connection.receive_data(data)
                for event in self._connection.events():
                    if isinstance(event, (_TextMessage, _BytesMessage)):
                        message = self._message_event(event)
                        if message is not None:
                            await self._receive_queue.put(message)
                    elif isinstance(event, _Ping):
                        await self._enqueue_raw(
                            self._connection.send(_Pong(payload=event.payload))
                        )
                    elif isinstance(event, _Pong):
                        self._last_pong_at = self._client._clock.monotonic()
                    elif isinstance(event, _CloseConnection):
                        with contextlib.suppress(HttpClientError):
                            await self._enqueue_raw(
                                self._connection.send(event.response())
                            )
                        self._fail(
                            WSClosedError(
                                "WebSocket peer initiated close",
                                code=int(event.code),
                                reason=event.reason,
                                **_error_context(self._request),
                            )
                        )
                        return
        except asyncio.CancelledError:
            raise
        except HttpClientError as exc:
            try:
                await self._hard_close()
            finally:
                self._fail(exc)
        except Exception as exc:  # noqa: BLE001 - seal wsproto at API boundary
            error = ProtocolError(
                f"invalid WebSocket frame: {exc}",
                **_error_context(self._request),
            )
            try:
                await self._hard_close()
            finally:
                self._fail(error)

    async def _write_loop(self) -> None:
        try:
            while True:
                item = await self._send_queue.get()
                if isinstance(item, _CloseItem):
                    await self._stream.write(
                        self._connection.send(_CloseConnection(code=item.code))
                    )
                    return
                await self._stream.write(item)
        except asyncio.CancelledError:
            raise
        except HttpClientError as exc:
            self._fail(exc)
        except Exception as exc:  # noqa: BLE001 - seal stream/protocol at boundary
            self._fail(
                ProtocolError(
                    f"WebSocket write failed: {exc}",
                    **_error_context(self._request),
                )
            )

    async def _heartbeat_loop(self) -> None:
        try:
            while not self._closed:
                await self._client._clock.sleep(self._heartbeat.interval)
                if self._closed:
                    return
                elapsed = self._client._clock.monotonic() - self._last_pong_at
                if elapsed > self._heartbeat.timeout:
                    self._fail(
                        WSClosedError(
                            "WebSocket heartbeat timed out",
                            code=None,
                            reason=None,
                            **_error_context(self._request),
                        )
                    )
                    await self._hard_close()
                    return
                await self._enqueue_raw(self._connection.send(_Ping()))
        except asyncio.CancelledError:
            raise
        except HttpClientError as exc:
            self._fail(exc)

    async def _enqueue_raw(self, raw: bytes) -> None:
        if self._closed:
            error = self._close_exc
            if error is not None:
                raise error
            raise WSClosedError(
                "WebSocket session is closed",
                code=None,
                reason=None,
                **_error_context(self._request),
            )
        try:
            async with asyncio.timeout(self._send_timeout):
                await self._send_queue.put(raw)
        except TimeoutError:
            raise WSQueueFullError(
                "WebSocket send queue remained full for "
                f"send_timeout={self._send_timeout}s",
                **_error_context(self._request),
            ) from None

    async def send_text(self, data: str) -> None:
        await self._enqueue_raw(self._connection.send(_TextMessage(data=data)))

    async def send_bytes(self, data: bytes) -> None:
        await self._enqueue_raw(self._connection.send(_BytesMessage(data=data)))

    async def send_model(self, model: TSend) -> None:
        if self._send_adapter is not None:
            try:
                validated = self._send_adapter.validate_python(model)
                encoded = self._send_adapter.dump_json(validated)
            except ValidationError as exc:
                raise MessageValidationError(
                    "invalid typed WebSocket outbound message",
                    **_error_context(self._request),
                ) from exc
            await self.send_text(encoded.decode("utf-8"))
            return
        dump = cast("BaseModel", model).model_dump_json()
        await self.send_text(dump)

    async def receive(self) -> WSMessage:
        if self._consumer_active:
            raise RuntimeError("WSSession already has an active receive consumer")
        if self._closed and self._receive_queue.empty():
            error = self._close_exc
            if error is not None:
                raise error
        self._consumer_active = True
        try:
            item = await self._receive_queue.get()
            if item is _RECEIVE_FAILURE:
                error = self._close_exc
                if error is not None:
                    raise error
                raise WSClosedError(
                    "WebSocket session is closed",
                    code=None,
                    reason=None,
                    **_error_context(self._request),
                )
            return cast("WSMessage", item)
        finally:
            self._consumer_active = False

    def stream(
        self,
        model: type[TMsg],
        *,
        on_invalid: Literal["raise", "skip"] = "raise",
    ) -> AsyncIterator[TMsg]:
        return self._stream_models(TypeAdapter(model), on_invalid=on_invalid)

    async def receive_typed(self) -> TRecv:
        if self._recv_adapter is None:
            raise RuntimeError("typed receive is unavailable on an imperative session")
        message = await self.receive()
        payload = message.text if message.kind == "text" else message.data
        if payload is None:
            raise RuntimeError("WebSocket message is missing its payload")
        try:
            return cast("TRecv", self._recv_adapter.validate_json(payload))
        except ValidationError as exc:
            raise MessageValidationError(
                "invalid typed WebSocket inbound message",
                **_error_context(self._request),
            ) from exc

    async def _stream_models(
        self,
        adapter: TypeAdapter[Any],
        *,
        on_invalid: Literal["raise", "skip"],
    ) -> AsyncIterator[Any]:
        if on_invalid not in {"raise", "skip"}:
            raise ValueError("on_invalid must be 'raise' or 'skip'")
        while True:
            message = await self.receive()
            payload = message.text if message.kind == "text" else message.data
            if payload is None:
                raise RuntimeError("WebSocket message is missing its payload")
            try:
                yield adapter.validate_json(payload)
            except ValidationError as exc:
                if on_invalid == "raise":
                    raise MessageValidationError(
                        "invalid typed WebSocket inbound message",
                        **_error_context(self._request),
                    ) from exc
                _LOGGER.debug("skipping invalid WebSocket message: %s", exc)

    def stream_typed(
        self,
        *,
        on_invalid: Literal["raise", "skip"] = "raise",
    ) -> AsyncIterator[TRecv]:
        if self._recv_adapter is None:
            raise RuntimeError("typed stream is unavailable on an imperative session")
        return cast(
            "AsyncIterator[TRecv]",
            self._stream_models(self._recv_adapter, on_invalid=on_invalid),
        )

    async def _cancel_tasks(self) -> None:
        current = asyncio.current_task()
        tasks = tuple(
            task
            for task in (
                self._reader_task,
                self._writer_task,
                self._heartbeat_task,
            )
            if task is not None and task is not current and not task.done()
        )
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _hard_close(self) -> None:
        self._client._infinite.discard(self)
        await self._cancel_tasks()
        if not self._stream_closed:
            self._stream_closed = True
            await self._stream.aclose()

    async def close(self, code: int = 1000) -> None:
        if not 1000 <= code <= 4999:
            raise ValueError("WebSocket close code must be between 1000 and 4999")
        if not self._closed:
            try:
                async with asyncio.timeout(self._send_timeout):
                    await self._send_queue.put(_CloseItem(code))
                    if self._writer_task is not None:
                        await self._writer_task
            except TimeoutError:
                pass
            self._fail(
                WSClosedError(
                    "WebSocket session closed",
                    code=code,
                    reason=None,
                    **_error_context(self._request),
                )
            )
        await self._hard_close()

    async def aclose(self) -> None:
        if not self._closed:
            self._fail(
                ClientClosedError(
                    "HttpClient closed while WebSocket receive was in flight",
                    **_error_context(self._request),
                )
            )
        await self._hard_close()


class WSSocket(Generic[TMsg]):
    """Simple typed one-connection WebSocket handle without reconnect."""

    def __init__(
        self,
        connection: WSConnect[TMsg, TMsg],
    ) -> None:
        self._connection = connection
        self._session: WSSession[TMsg, TMsg] | None = None

    async def __aenter__(self) -> WSSocket[TMsg]:
        self._session = await self._connection.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        await self._connection.__aexit__(exc_type, exc, tb)

    @property
    def subprotocol(self) -> str | None:
        return self._require_session().subprotocol

    def _require_session(self) -> WSSession[TMsg, TMsg]:
        if self._session is None:
            raise RuntimeError("WSSocket must be entered before use")
        return self._session

    async def send(self, message: TMsg) -> None:
        await self._require_session().send_model(message)

    async def receive(self) -> TMsg:
        return await self._require_session().receive_typed()

    def stream(
        self,
        *,
        on_invalid: Literal["raise", "skip"] = "raise",
    ) -> AsyncIterator[TMsg]:
        return self._require_session().stream_typed(on_invalid=on_invalid)


class _CallableWSModule(ModuleType):
    """Keep ``from rapidy_client import ws`` callable after submodule loading."""

    def __call__(
        self,
        path: str,
        *,
        heartbeat: Heartbeat | None = None,
        max_message_size: int = 16_777_216,
        receive_queue_limit: int = 256,
        send_queue_limit: int = 256,
        send_timeout: float = 10.0,
        subprotocols: Sequence[str] = (),
    ) -> Any:
        from rapidy_client._typed import ws

        return ws(
            path,
            heartbeat=heartbeat,
            max_message_size=max_message_size,
            receive_queue_limit=receive_queue_limit,
            send_queue_limit=send_queue_limit,
            send_timeout=send_timeout,
            subprotocols=subprotocols,
        )


sys.modules[__name__].__class__ = _CallableWSModule
