from __future__ import annotations

from collections.abc import AsyncIterator

from rapidy import Rapidy
from rapidy.http import get, SSEResponse, StreamResponse, WebSocket, websocket
from rapidy.responses import SSEEvent


@websocket('/ws')
async def echo(web_socket: WebSocket) -> None:
    """Echo WebSocket text and binary messages."""
    await web_socket.accept()
    async for message in web_socket:
        if isinstance(message, str):
            await web_socket.send_text(message)
        else:
            await web_socket.send_bytes(message)


async def events() -> AsyncIterator[SSEEvent]:
    """Yield a small event stream."""
    for index in range(3):
        yield SSEEvent({'index': index}, event='tick', id=str(index))


@get('/events')
async def event_stream() -> SSEResponse:
    """Return a Server-Sent Events response."""
    return SSEResponse(events(), retry=2000)


async def chunks() -> AsyncIterator[bytes]:
    """Yield two incremental response chunks."""
    yield b'first\n'
    yield b'second\n'


@get('/download')
async def download() -> StreamResponse:
    """Return a generic streaming response."""
    return StreamResponse(chunks(), content_type='text/plain', charset='utf-8')


app = Rapidy(http_route_handlers=[echo, event_stream, download])
