from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterable, AsyncIterator, Mapping
from contextlib import suppress
from enum import Enum
from typing import Any, NamedTuple, TYPE_CHECKING

from multidict import CIMultiDict
from rapidy_core.enums import Charset, ContentType

from rapidy._base_exceptions import RapidyException
from rapidy.constants import DEFAULT_JSON_ENCODER
from rapidy.typedefs import ASGIMessage, LooseHeaders, Receive, Send
from rapidy.version import SERVER_INFO

if TYPE_CHECKING:
    from rapidy.background import Background, BackgroundCallable, BackgroundRunner
    from rapidy.request import Request

__all__ = ('SSEEvent', 'SSEResponse', 'StreamResponse')

logger = logging.getLogger('rapidy')


class StreamNotPreparedError(RapidyException):
    """Raised when imperative writes precede ``prepare``."""

    message = 'StreamResponse is not prepared yet. Call `prepare(request)` before `write` / `write_eof`.'


class StreamAlreadyFinishedError(RapidyException):
    """Raised when an imperative write follows the final frame."""

    message = 'StreamResponse is already finished. `{action}` is not allowed after `write_eof`.'


class _ClientDisconnectedError(Exception):
    """Internal marker for server-specific send failures after disconnect."""


class SSEEvent(NamedTuple):
    """One Server-Sent Event payload with optional metadata."""

    data: str | dict[str, Any]
    event: str | None = None
    id: str | None = None


class StreamResponse:
    """Incremental HTTP response supporting iterable and imperative writes."""

    __slots__ = (
        '_body',
        '_background',
        '_charset',
        '_content_type',
        '_eof_sent',
        '_headers',
        '_http_version',
        '_send_fn',
        '_sent',
        '_server_info',
        '_started',
        '_status',
    )

    def __init__(
        self,
        body: AsyncIterable[bytes | str] | None = None,
        *,
        status: int = 200,
        headers: LooseHeaders | None = None,
        content_type: str | ContentType = ContentType.stream,
        charset: str | Charset | None = None,
        background: Background | BackgroundCallable | None = None,
    ) -> None:
        from rapidy.background import normalize_background  # noqa: PLC0415

        self._body = body
        self._background = normalize_background(background)
        self._status = status
        self._headers = _make_headers(headers)
        self._content_type = _enum_value(content_type)
        self._charset = _optional_enum_value(charset)
        self._send_fn: Send | None = None
        self._http_version = '1.1'
        self._server_info: str | None = None
        self._started = False
        self._eof_sent = False
        self._sent = False

    @property
    def status(self) -> int:
        """Return the response status."""
        return self._status

    @status.setter
    def status(self, value: int) -> None:
        self._status = value

    @property
    def background(self) -> BackgroundRunner | None:
        """Return the post-response task attached to this response."""
        return self._background

    @background.setter
    def background(self, value: Background | BackgroundCallable | None) -> None:
        from rapidy.background import normalize_background  # noqa: PLC0415

        self._background = normalize_background(value)

    @property
    def headers(self) -> CIMultiDict[str]:
        """Return the mutable response headers."""
        return self._headers

    @property
    def content_type(self) -> str:
        """Return the response media type."""
        return self._content_type

    @content_type.setter
    def content_type(self, value: str | ContentType) -> None:
        self._content_type = _enum_value(value)

    @property
    def charset(self) -> str | None:
        """Return the explicit stream charset."""
        return self._charset

    @charset.setter
    def charset(self, value: str | Charset | None) -> None:
        self._charset = _optional_enum_value(value)

    async def prepare(self, request: Request) -> None:
        """Send the response start frame once and bind the request transport."""
        if self._started:
            return
        from rapidy.middlewares._utils import apply_response_hooks  # noqa: PLC0415

        finalized = await apply_response_hooks(request, self)
        if finalized is not self:
            msg = 'Streaming response hooks cannot replace a response during prepare()'
            raise RuntimeError(msg)
        self._send_fn = request._asgi_send  # noqa: SLF001
        self._http_version = str(request.scope.get('http_version', '1.1'))
        self._server_info = SERVER_INFO if request.app.server_info_in_response else None
        await self._start(self._send_fn)

    async def write(self, data: bytes) -> None:
        """Send one imperative body chunk."""
        if self._eof_sent:
            raise StreamAlreadyFinishedError(action='write')
        if not self._started or self._send_fn is None:
            raise StreamNotPreparedError
        await self._send_fn({'type': 'http.response.body', 'body': data, 'more_body': True})

    async def write_eof(self, data: bytes = b'') -> None:
        """Send the final imperative body frame once."""
        if self._eof_sent:
            return
        if not self._started or self._send_fn is None:
            raise StreamNotPreparedError
        await self._send_fn({'type': 'http.response.body', 'body': data, 'more_body': False})
        self._eof_sent = True
        self._sent = True

    async def _send_stream(
        self,
        send: Send,
        receive: Receive,
        *,
        server_info: str | None = None,
    ) -> None:
        if self._sent:
            return
        if not self._started:
            if server_info is not None:
                self._server_info = server_info
            self._send_fn = send
            await self._start(send)

        stream_task = asyncio.create_task(self._iterate_and_send(send))
        listen_task = asyncio.create_task(self._listen_for_disconnect(receive))
        try:
            done, _pending = await asyncio.wait(
                {stream_task, listen_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if stream_task in done:
                await _cancel_and_wait(listen_task)
                try:
                    await stream_task
                except _ClientDisconnectedError:
                    await self._aclose_body()
                except Exception as exc:
                    logger.exception('Unhandled error while streaming response body', exc_info=exc)
                    await self._aclose_body()
                    try:
                        await self._guarded_send(
                            send,
                            {'type': 'http.response.body', 'body': b'', 'more_body': False},
                        )
                    except _ClientDisconnectedError:
                        pass
                    else:
                        self._eof_sent = True
            else:
                await _cancel_and_wait(stream_task)
                await self._aclose_body()
        finally:
            await _cancel_and_wait(stream_task)
            await _cancel_and_wait(listen_task)
            self._sent = True

    async def _iterate_and_send(self, send: Send) -> None:
        if self._body is not None:
            async for chunk in self._body:
                data = chunk.encode(self._charset or 'utf-8') if isinstance(chunk, str) else chunk
                await self._guarded_send(
                    send,
                    {'type': 'http.response.body', 'body': data, 'more_body': True},
                )
        await self._guarded_send(
            send,
            {'type': 'http.response.body', 'body': b'', 'more_body': False},
        )
        self._eof_sent = True

    @staticmethod
    async def _guarded_send(send: Send, message: ASGIMessage) -> None:
        try:
            await send(message)
        except Exception as exc:
            raise _ClientDisconnectedError from exc

    @staticmethod
    async def _listen_for_disconnect(receive: Receive) -> None:
        while True:
            message = await receive()
            if message.get('type') == 'http.disconnect':
                return

    async def _aclose_body(self) -> None:
        close = getattr(self._body, 'aclose', None)
        if close is not None:
            await close()

    async def _start(self, send: Send) -> None:
        await send(self._start_payload())
        self._started = True

    def _start_payload(self) -> ASGIMessage:
        headers = CIMultiDict(self._headers)
        if not self._preserve_content_length():
            headers.popall('content-length', None)
        headers.popall('transfer-encoding', None)
        if 'content-type' not in headers:
            content_type = self._content_type
            if self._charset is not None:
                content_type = f'{content_type}; charset={self._charset}'
            headers['content-type'] = content_type
        for name, value in self._default_headers():
            if name not in headers:
                headers[name] = value
        if self._server_info is not None and 'server' not in headers:
            headers['server'] = self._server_info
        encoded_headers = [(name.encode('latin-1'), value.encode('latin-1')) for name, value in headers.items()]
        return {'type': 'http.response.start', 'status': self._status, 'headers': encoded_headers}

    def _preserve_content_length(self) -> bool:
        return False

    def _default_headers(self) -> list[tuple[str, str]]:
        return []


class SSEResponse(StreamResponse):
    """Incremental ``text/event-stream`` response."""

    __slots__ = ('_events', '_retry')

    def __init__(
        self,
        events: AsyncIterable[SSEEvent | str | dict[str, Any]],
        *,
        status: int = 200,
        headers: LooseHeaders | None = None,
        retry: int | None = None,
        background: Background | BackgroundCallable | None = None,
    ) -> None:
        self._events = events
        self._retry = retry
        super().__init__(
            body=self._frames(),
            status=status,
            headers=headers,
            content_type='text/event-stream',
            charset=Charset.utf8,
            background=background,
        )

    async def _frames(self) -> AsyncIterator[str]:
        try:
            if self._retry is not None:
                yield f'retry: {self._retry}\n\n'
            async for event in self._events:
                yield _render_sse_frame(event)
        finally:
            close = getattr(self._events, 'aclose', None)
            if close is not None:
                await close()

    def _default_headers(self) -> list[tuple[str, str]]:
        defaults = [('Cache-Control', 'no-cache')]
        # Connection is hop-by-hop and therefore invalid in HTTP/2 and HTTP/3.
        if self._http_version in ('1.0', '1.1'):
            defaults.append(('Connection', 'keep-alive'))
        return defaults


def _render_sse_frame(payload: SSEEvent | str | dict[str, Any]) -> str:
    event_name: str | None = None
    event_id: str | None = None
    if isinstance(payload, SSEEvent):
        event_name = payload.event
        event_id = payload.id
        data = payload.data
    else:
        data = payload

    text = DEFAULT_JSON_ENCODER(data) if isinstance(data, dict) else data
    lines: list[str] = []
    if event_id is not None:
        lines.append(f'id: {event_id}')
    if event_name is not None:
        lines.append(f'event: {event_name}')
    lines.extend(f'data: {line}' for line in text.split('\n'))
    return f"{'\n'.join(lines)}\n\n"


async def _cancel_and_wait(task: asyncio.Task[Any]) -> None:
    if not task.done():
        task.cancel()
    with suppress(asyncio.CancelledError, Exception):
        await task


def _as_header_text(value: str | bytes) -> str:
    return value.decode('latin-1') if isinstance(value, bytes) else value


def _make_headers(headers: LooseHeaders | None) -> CIMultiDict[str]:
    if headers is None:
        return CIMultiDict()
    if isinstance(headers, Mapping):
        return CIMultiDict(headers)
    return CIMultiDict((_as_header_text(name), _as_header_text(value)) for name, value in headers)


def _enum_value(value: str | Enum) -> str:
    return str(value.value) if isinstance(value, Enum) else value


def _optional_enum_value(value: str | Enum | None) -> str | None:
    return None if value is None else _enum_value(value)
