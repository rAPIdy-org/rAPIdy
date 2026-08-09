from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator, Mapping
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self
from urllib.parse import urlsplit

import httpx
from anyio.from_thread import BlockingPortal  # noqa: TC002 - runtime annotations

from rapidy.constants import DEFAULT_JSON_DECODER
from rapidy.typedefs import ASGIMessage, ASGIScope, JSONDecoder

__all__ = ('AsyncSSESession', 'SSESession', 'ServerSentEvent')


@dataclass(frozen=True, slots=True)
class ServerSentEvent:
    """One parsed Server-Sent Event received by a test client."""

    data: str
    event: str | None = None
    id: str | None = None
    retry: int | None = None

    def json(self, *, loads: JSONDecoder = DEFAULT_JSON_DECODER) -> Any:
        """Decode the event data as JSON."""
        return loads(self.data)


class AsyncSSESession:
    """Incremental in-process reader for one finite or live SSE response."""

    __slots__ = (
        '_app',
        '_buffer',
        '_client',
        '_completed',
        '_headers',
        '_incoming',
        '_outgoing',
        '_path',
        '_pending',
        '_root_path',
        '_task',
        'headers',
        'retry',
        'status_code',
    )

    def __init__(
        self,
        app: Any,
        path: str,
        *,
        root_path: str,
        client: tuple[str, int],
        headers: Mapping[str, str] | None,
    ) -> None:
        self._app = app
        self._path = path
        self._root_path = root_path
        self._client = client
        self._headers = dict(headers or {})
        self._incoming: asyncio.Queue[ASGIMessage] = asyncio.Queue()
        self._outgoing: asyncio.Queue[ASGIMessage] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._buffer = bytearray()
        self._pending: list[ServerSentEvent] = []
        self._completed = False
        self.status_code = 0
        self.headers = httpx.Headers()
        self.retry: int | None = None

    async def __aenter__(self) -> Self:
        """Start the HTTP stream and validate its SSE content type."""
        if self._task is not None:
            msg = 'SSE test session is already entered'
            raise RuntimeError(msg)
        parsed = urlsplit(self._path)
        path = parsed.path or '/'
        scope: ASGIScope = {
            'type': 'http',
            'asgi': {'version': '3.0', 'spec_version': '2.5'},
            'http_version': '1.1',
            'scheme': 'http',
            'method': 'GET',
            'path': path,
            'raw_path': path.encode(),
            'query_string': parsed.query.encode(),
            'root_path': self._root_path,
            'headers': [(name.lower().encode(), value.encode()) for name, value in self._headers.items()],
            'client': self._client,
            'server': ('testserver', 80),
            'state': {},
        }
        self._task = asyncio.create_task(
            self._app(scope, self._incoming.get, self._outgoing.put),
            name='rapidy-test-sse',
        )
        await self._incoming.put({'type': 'http.request', 'body': b'', 'more_body': False})
        message = await self._receive_from_app()
        if message.get('type') != 'http.response.start':
            await self.close()
            msg = f"Unexpected SSE start message: {message.get('type')!r}"
            raise RuntimeError(msg)
        self.status_code = int(message.get('status', 0))
        self.headers = httpx.Headers(message.get('headers', []))
        if self.headers.get('content-type', '').split(';', 1)[0].strip() != 'text/event-stream':
            await self.close()
            msg = 'SSE endpoint must respond with `text/event-stream`'
            raise RuntimeError(msg)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Disconnect the stream and wait for application cleanup."""
        await self.close()

    def __aiter__(self) -> AsyncIterator[ServerSentEvent]:
        return self

    async def __anext__(self) -> ServerSentEvent:
        while not self._pending:
            if self._completed:
                raise StopAsyncIteration
            message = await self._receive_from_app()
            if message.get('type') != 'http.response.body':
                msg = f"Unexpected SSE body message: {message.get('type')!r}"
                raise RuntimeError(msg)
            self._buffer.extend(bytes(message.get('body', b'')))
            self._parse_frames(final=not bool(message.get('more_body', False)))
            if not message.get('more_body', False):
                self._completed = True
                await self._wait_for_task()
        return self._pending.pop(0)

    async def receive_event(self) -> ServerSentEvent:
        """Receive and parse the next dispatched SSE event."""
        return await self.__anext__()

    async def close(self) -> None:
        """Disconnect the HTTP peer and wait for the stream task."""
        task = self._task
        if task is None:
            return
        if not task.done():
            await self._incoming.put({'type': 'http.disconnect'})
        await self._wait_for_task()
        self._completed = True

    def _parse_frames(self, *, final: bool) -> None:
        normalized = bytes(self._buffer).replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        frames = normalized.split(b'\n\n')
        remainder = frames.pop()
        if final and remainder:
            frames.append(remainder)
            remainder = b''
        self._buffer = bytearray(remainder)
        for frame in frames:
            event = self._parse_frame(frame.decode('utf-8'))
            if event is not None:
                self._pending.append(event)

    def _parse_frame(self, frame: str) -> ServerSentEvent | None:
        data: list[str] = []
        event_name: str | None = None
        event_id: str | None = None
        frame_retry: int | None = None
        for line in frame.split('\n'):
            if not line or line.startswith(':'):
                continue
            field, separator, value = line.partition(':')
            if separator and value.startswith(' '):
                value = value[1:]
            if field == 'data':
                data.append(value)
            elif field == 'event':
                event_name = value
            elif field == 'id' and '\x00' not in value:
                event_id = value
            elif field == 'retry' and value.isdecimal():
                frame_retry = int(value)
                self.retry = frame_retry
        if not data:
            return None
        return ServerSentEvent(data='\n'.join(data), event=event_name, id=event_id, retry=frame_retry)

    async def _receive_from_app(self) -> ASGIMessage:
        task = self._task
        if task is None:
            msg = 'SSE test session is not connected'
            raise RuntimeError(msg)
        message_task = asyncio.create_task(self._outgoing.get())
        done, _pending = await asyncio.wait((message_task, task), return_when=asyncio.FIRST_COMPLETED)
        if message_task in done:
            return message_task.result()
        message_task.cancel()
        await asyncio.gather(message_task, return_exceptions=True)
        await self._wait_for_task()
        msg = 'SSE application completed before finishing the response'
        raise RuntimeError(msg)

    async def _wait_for_task(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            await task


class SSESession:
    """Synchronous facade over an incremental asynchronous SSE session."""

    __slots__ = ('_async_session', '_portal')

    def __init__(self, async_session: AsyncSSESession, portal: BlockingPortal) -> None:
        self._async_session = async_session
        self._portal = portal

    @property
    def status_code(self) -> int:
        """Return the HTTP status received at stream start."""
        return self._async_session.status_code

    @property
    def headers(self) -> httpx.Headers:
        """Return the HTTP response headers."""
        return self._async_session.headers

    @property
    def retry(self) -> int | None:
        """Return the most recently received reconnection delay."""
        return self._async_session.retry

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

    def __iter__(self) -> Iterator[ServerSentEvent]:
        return self

    def __next__(self) -> ServerSentEvent:
        try:
            return self.receive_event()
        except StopAsyncIteration:
            raise StopIteration from None

    def receive_event(self) -> ServerSentEvent:
        """Receive and parse the next dispatched SSE event."""
        return self._portal.call(self._async_session.receive_event)

    def close(self) -> None:
        """Disconnect the stream."""
        self._portal.call(self._async_session.close)
