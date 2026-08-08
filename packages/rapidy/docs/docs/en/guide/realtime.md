# WebSockets, SSE, and streaming

## WebSocket

WebSocket routes use `@websocket`, not an HTTP `@get` handler. Header, cookie, path, and query extraction works during
the handshake; request bodies are not valid WebSocket parameters.

```python
from rapidy import Rapidy
from rapidy.http import WebSocket, websocket


@websocket('/ws')
async def echo(web_socket: WebSocket) -> None:
    await web_socket.accept()
    async for message in web_socket:
        if isinstance(message, str):
            await web_socket.send_text(message)
        else:
            await web_socket.send_bytes(message)


app = Rapidy(http_route_handlers=[echo])
```

`WebSocket` supports text, bytes, JSON, subprotocols, headers, async iteration, and explicit close/reject. A client
disconnect raises `WebSocketDisconnect`. Accepted connections receive close code 1001 during application shutdown.

## Server-Sent Events

```python
from collections.abc import AsyncIterator

from rapidy.http import get, SSEResponse
from rapidy.responses import SSEEvent


async def events() -> AsyncIterator[SSEEvent]:
    for index in range(3):
        yield SSEEvent({'index': index}, event='tick', id=str(index))


@get('/events')
async def event_stream() -> SSEResponse:
    return SSEResponse(events(), retry=2000)
```

`SSEResponse` emits `text/event-stream; charset=utf-8`, `Cache-Control: no-cache`, multiline frames, optional event
name/id, and retry metadata. It never sets `Content-Length`.

## Generic streaming

Return `StreamResponse(async_iterable, content_type=...)` for incremental bytes or text. For imperative streaming,
return a response whose handler or downstream code uses `prepare(request)`, `write(bytes)`, then `write_eof()`.
Client disconnect closes the async iterable and request-scoped DI finalizers still run.

All three examples are combined in
[`examples/realtime.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/realtime.py).
