from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from functools import partial
from types import TracebackType
from typing import Any, cast, Self, TYPE_CHECKING
from urllib.parse import urlsplit

from rapidy.constants import DEFAULT_JSON_DECODER, DEFAULT_JSON_ENCODER
from rapidy.typedefs import ASGIMessage, ASGIScope, JSONDecoder, JSONEncoder
from rapidy.websockets import WebSocketDisconnect

if TYPE_CHECKING:
    from anyio.from_thread import BlockingPortal

__all__ = ('AsyncWebSocketSession', 'WebSocketSession')


class AsyncWebSocketSession:
    """In-process asynchronous WebSocket peer for a running test client."""

    __slots__ = (
        '_app',
        '_client',
        '_incoming',
        '_outgoing',
        '_path',
        '_root_path',
        '_task',
        'accepted_headers',
        'accepted_subprotocol',
        'headers',
        'subprotocols',
    )

    def __init__(
        self,
        app: Any,
        path: str,
        *,
        root_path: str,
        client: tuple[str, int],
        headers: Mapping[str, str] | None,
        subprotocols: Sequence[str],
    ) -> None:
        self._app = app
        self._path = path
        self._root_path = root_path
        self._client = client
        self.headers = dict(headers or {})
        self.subprotocols = tuple(subprotocols)
        self.accepted_subprotocol: str | None = None
        self.accepted_headers: tuple[tuple[bytes, bytes], ...] = ()
        self._incoming: asyncio.Queue[ASGIMessage] = asyncio.Queue()
        self._outgoing: asyncio.Queue[ASGIMessage] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> Self:
        """Connect and require an accepted WebSocket handshake."""
        if self._task is not None:
            msg = 'WebSocket test session is already entered'
            raise RuntimeError(msg)
        parsed = urlsplit(self._path)
        path = parsed.path or '/'
        scope: ASGIScope = {
            'type': 'websocket',
            'asgi': {'version': '3.0', 'spec_version': '2.5'},
            'http_version': '1.1',
            'scheme': 'ws',
            'path': path,
            'raw_path': path.encode(),
            'query_string': parsed.query.encode(),
            'root_path': self._root_path,
            'headers': [(name.lower().encode(), value.encode()) for name, value in self.headers.items()],
            'client': self._client,
            'server': ('testserver', 80),
            'subprotocols': list(self.subprotocols),
            'state': {},
        }
        self._task = asyncio.create_task(
            self._app(scope, self._incoming.get, self._outgoing.put),
            name='rapidy-test-websocket',
        )
        await self._incoming.put({'type': 'websocket.connect'})
        message = await self._receive_from_app()
        message_type = message.get('type')
        if message_type == 'websocket.close':
            await self._wait_for_task()
            raise WebSocketDisconnect(
                code=int(message.get('code', 1000)),
                reason=str(message.get('reason') or ''),
            )
        if message_type != 'websocket.accept':
            await self.close(code=1002)
            msg = f'Unexpected WebSocket handshake message: {message_type!r}'
            raise RuntimeError(msg)
        self.accepted_subprotocol = cast('str | None', message.get('subprotocol'))
        self.accepted_headers = tuple(cast('list[tuple[bytes, bytes]]', message.get('headers', [])))
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Disconnect the client peer and wait for application cleanup."""
        await self.close()

    async def send_text(self, data: str) -> None:
        """Send one text frame to the application."""
        self._ensure_connected()
        await self._incoming.put({'type': 'websocket.receive', 'text': data})

    async def send_bytes(self, data: bytes) -> None:
        """Send one binary frame to the application."""
        self._ensure_connected()
        await self._incoming.put({'type': 'websocket.receive', 'bytes': data})

    async def send_json(self, value: Any, *, dumps: JSONEncoder = DEFAULT_JSON_ENCODER) -> None:
        """Encode and send one JSON text frame."""
        await self.send_text(dumps(value))

    async def receive_text(self) -> str:
        """Receive one text frame from the application."""
        message = await self._receive_data()
        if 'text' not in message:
            msg = 'Expected a WebSocket text frame, received bytes'
            raise TypeError(msg)
        return cast('str', message['text'])

    async def receive_bytes(self) -> bytes:
        """Receive one binary frame from the application."""
        message = await self._receive_data()
        if 'bytes' not in message:
            msg = 'Expected a WebSocket bytes frame, received text'
            raise TypeError(msg)
        return cast('bytes', message['bytes'])

    async def receive_json(self, *, loads: JSONDecoder = DEFAULT_JSON_DECODER) -> Any:
        """Receive and decode one JSON text frame."""
        return loads(await self.receive_text())

    async def close(self, *, code: int = 1000, reason: str = '') -> None:
        """Disconnect the client peer and wait for the application task."""
        task = self._task
        if task is None:
            return
        if not task.done():
            await self._incoming.put({'type': 'websocket.disconnect', 'code': code, 'reason': reason})
        await self._wait_for_task()

    async def _receive_data(self) -> ASGIMessage:
        self._ensure_connected()
        message = await self._receive_from_app()
        message_type = message.get('type')
        if message_type == 'websocket.close':
            await self._wait_for_task()
            raise WebSocketDisconnect(
                code=int(message.get('code', 1000)),
                reason=str(message.get('reason') or ''),
            )
        if message_type != 'websocket.send':
            msg = f'Unexpected ASGI WebSocket message: {message_type!r}'
            raise RuntimeError(msg)
        return message

    async def _receive_from_app(self) -> ASGIMessage:
        task = self._task
        if task is None:
            msg = 'WebSocket test session is not connected'
            raise RuntimeError(msg)
        message_task = asyncio.create_task(self._outgoing.get())
        done, _pending = await asyncio.wait((message_task, task), return_when=asyncio.FIRST_COMPLETED)
        if message_task in done:
            return message_task.result()
        message_task.cancel()
        await asyncio.gather(message_task, return_exceptions=True)
        await self._wait_for_task()
        msg = 'WebSocket application completed without sending a closing frame'
        raise RuntimeError(msg)

    async def _wait_for_task(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            await task

    def _ensure_connected(self) -> None:
        if self._task is None:
            msg = 'WebSocket test session is not connected'
            raise RuntimeError(msg)


class WebSocketSession:
    """Synchronous facade over an asynchronous in-process WebSocket peer."""

    __slots__ = ('_async_session', '_portal')

    def __init__(self, async_session: AsyncWebSocketSession, portal: BlockingPortal) -> None:
        self._async_session = async_session
        self._portal = portal

    @property
    def accepted_subprotocol(self) -> str | None:
        """Return the subprotocol selected by the application."""
        return self._async_session.accepted_subprotocol

    @property
    def accepted_headers(self) -> tuple[tuple[bytes, bytes], ...]:
        """Return additional headers sent with the accepted handshake."""
        return self._async_session.accepted_headers

    def __enter__(self) -> Self:
        self._portal.call(self._async_session.__aenter__)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._portal.call(self._async_session.close)

    def send_text(self, data: str) -> None:
        """Send one text frame to the application."""
        self._portal.call(self._async_session.send_text, data)

    def send_bytes(self, data: bytes) -> None:
        """Send one binary frame to the application."""
        self._portal.call(self._async_session.send_bytes, data)

    def send_json(self, value: Any, *, dumps: JSONEncoder = DEFAULT_JSON_ENCODER) -> None:
        """Encode and send one JSON text frame."""
        self._portal.call(partial(self._async_session.send_json, value, dumps=dumps))

    def receive_text(self) -> str:
        """Receive one text frame from the application."""
        return self._portal.call(self._async_session.receive_text)

    def receive_bytes(self) -> bytes:
        """Receive one binary frame from the application."""
        return self._portal.call(self._async_session.receive_bytes)

    def receive_json(self, *, loads: JSONDecoder = DEFAULT_JSON_DECODER) -> Any:
        """Receive and decode one JSON text frame."""
        return self._portal.call(partial(self._async_session.receive_json, loads=loads))

    def close(self, *, code: int = 1000, reason: str = '') -> None:
        """Disconnect the client peer."""
        self._portal.call(partial(self._async_session.close, code=code, reason=reason))
