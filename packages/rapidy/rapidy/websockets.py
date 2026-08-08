from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from enum import Enum
from typing import Any, cast

from multidict import CIMultiDict, CIMultiDictProxy

from rapidy._base_exceptions import RapidyException
from rapidy.constants import DEFAULT_JSON_DECODER, DEFAULT_JSON_ENCODER
from rapidy.typedefs import ASGIScope, JSONDecoder, JSONEncoder, LooseHeaders, Receive, Send

__all__ = ('WebSocket', 'WebSocketDisconnect')


class WebSocketState(Enum):
    """Internal state shared by the client and application sides of a connection."""

    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'


class WebSocketDisconnect(Exception):  # noqa: N818 - public compatibility name
    """Signal that the peer closed a WebSocket connection."""

    def __init__(self, code: int, reason: str = '') -> None:
        self.code = code
        self.reason = reason
        super().__init__(code, reason)


class WebSocketNotAcceptedError(RapidyException):
    """Raised when data operations precede handshake acceptance."""

    message = 'WebSocket connection is not accepted yet. Call `accept` before `receive_*` / `send_*`.'


class WebSocketClosedError(RapidyException):
    """Raised when an operation targets a closed connection."""

    message = 'WebSocket connection is closed. `{action}` is not allowed.'


class WebSocketFrameTypeError(RapidyException):
    """Raised when a typed receive method gets the other frame kind."""

    message = 'Unexpected WebSocket frame: expected `{expected}` frame, received `{received}`.'


class WebSocket:
    """Stateful ASGI WebSocket connection wrapper."""

    __slots__ = (
        '_application_state',
        '_client_state',
        '_headers',
        '_receive',
        '_scope',
        '_send',
        'path_params',
    )

    def __init__(self, scope: ASGIScope, receive: Receive, send: Send) -> None:
        self._scope = scope
        self._receive = receive
        self._send = send
        self._client_state = WebSocketState.CONNECTING
        self._application_state = WebSocketState.CONNECTING
        self._headers: CIMultiDictProxy[str] | None = None
        self.path_params: dict[str, str] = {}

    @property
    def path(self) -> str:
        """Return the path from the ASGI scope."""
        return str(self._scope['path'])

    @property
    def headers(self) -> CIMultiDictProxy[str]:
        """Return lazily decoded, case-insensitive handshake headers."""
        if self._headers is None:
            mutable_headers = CIMultiDict(
                (bytes(name).decode('latin-1'), bytes(value).decode('latin-1'))
                for name, value in cast('list[tuple[bytes, bytes]]', self._scope.get('headers', []))
            )
            self._headers = CIMultiDictProxy(mutable_headers)
        return self._headers

    @property
    def query_string(self) -> str:
        """Return the raw query string decoded losslessly."""
        return cast('bytes', self._scope.get('query_string', b'')).decode('latin-1')

    @property
    def subprotocols(self) -> list[str]:
        """Return the client-offered subprotocols."""
        return list(cast('list[str]', self._scope.get('subprotocols', [])))

    @property
    def client_state(self) -> WebSocketState:
        """Return the current peer-side state."""
        return self._client_state

    @property
    def application_state(self) -> WebSocketState:
        """Return the current application-side state."""
        return self._application_state

    async def accept(self, subprotocol: str | None = None, headers: LooseHeaders | None = None) -> None:
        """Consume the connect event and accept the WebSocket handshake."""
        if self._application_state is WebSocketState.CONNECTED:
            # Repeated acceptance is deliberately idempotent.
            return
        if self._application_state is WebSocketState.DISCONNECTED:
            raise WebSocketClosedError(action='accept')
        if self._client_state is WebSocketState.CONNECTING:
            await self._consume_connect()
        await self._send(
            {
                'type': 'websocket.accept',
                'subprotocol': subprotocol,
                'headers': _encode_headers(headers),
            }
        )
        self._application_state = WebSocketState.CONNECTED

    async def receive_text(self) -> str:
        """Receive one text frame."""
        message = await self._receive_message()
        text = message.get('text')
        if text is None:
            raise WebSocketFrameTypeError(expected='text', received='bytes')
        return cast('str', text)

    async def receive_bytes(self) -> bytes:
        """Receive one binary frame."""
        message = await self._receive_message()
        data = message.get('bytes')
        if data is None:
            raise WebSocketFrameTypeError(expected='bytes', received='text')
        return cast('bytes', data)

    async def receive_json(self, *, loads: JSONDecoder = DEFAULT_JSON_DECODER) -> Any:
        """Receive and decode one JSON text frame."""
        return loads(await self.receive_text())

    async def send_text(self, data: str) -> None:
        """Send one text frame."""
        self._ensure_connected(action='send')
        await self._send({'type': 'websocket.send', 'text': data})

    async def send_bytes(self, data: bytes) -> None:
        """Send one binary frame."""
        self._ensure_connected(action='send')
        await self._send({'type': 'websocket.send', 'bytes': data})

    async def send_json(self, obj: Any, *, dumps: JSONEncoder = DEFAULT_JSON_ENCODER) -> None:
        """Encode and send one JSON text frame."""
        await self.send_text(dumps(obj))

    async def close(self, code: int = 1000, reason: str = '') -> None:
        """Close or reject the connection, idempotently."""
        if self._application_state is WebSocketState.DISCONNECTED:
            return
        if self._client_state is WebSocketState.CONNECTING:
            await self._consume_connect()
        await self._send({'type': 'websocket.close', 'code': code, 'reason': reason})
        self._application_state = WebSocketState.DISCONNECTED

    def __aiter__(self) -> AsyncIterator[str | bytes]:
        return self

    async def __anext__(self) -> str | bytes:
        try:
            message = await self._receive_message()
        except WebSocketDisconnect:
            raise StopAsyncIteration from None
        text = message.get('text')
        if text is not None:
            return cast('str', text)
        return cast('bytes', message['bytes'])

    async def _consume_connect(self) -> None:
        message = await self._receive()
        if message.get('type') != 'websocket.connect':
            msg = f'Expected `websocket.connect`, received `{message.get("type")}`.'
            raise RuntimeError(msg)
        self._client_state = WebSocketState.CONNECTED

    async def _receive_message(self) -> dict[str, Any]:
        self._ensure_connected(action='receive')
        message = await self._receive()
        message_type = message.get('type')
        if message_type == 'websocket.disconnect':
            self._client_state = WebSocketState.DISCONNECTED
            self._application_state = WebSocketState.DISCONNECTED
            raise WebSocketDisconnect(
                code=int(message.get('code', 1000)),
                reason=str(message.get('reason') or ''),
            )
        if message_type != 'websocket.receive':
            msg = f'Unexpected ASGI WebSocket message: {message_type!r}'
            raise RuntimeError(msg)
        return message

    def _ensure_connected(self, *, action: str) -> None:
        if self._application_state is WebSocketState.CONNECTING:
            raise WebSocketNotAcceptedError
        if self._application_state is WebSocketState.DISCONNECTED:
            raise WebSocketClosedError(action=action)


def _as_header_bytes(value: str | bytes) -> bytes:
    return value if isinstance(value, bytes) else value.encode('latin-1')


def _encode_headers(headers: LooseHeaders | None) -> list[tuple[bytes, bytes]]:
    if headers is None:
        return []
    items = headers.items() if isinstance(headers, Mapping) else headers
    return [(_as_header_bytes(name), _as_header_bytes(value)) for name, value in items]
