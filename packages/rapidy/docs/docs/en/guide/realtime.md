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
disconnect, including a transport failure during `send`, raises `WebSocketDisconnect` without an application-error
traceback. During direct lifespan shutdown rAPIdy requests code 1001 for still-open accepted connections; a process
server may close them earlier with its own orderly restart code, so signal behavior is runtime-specific.
HTTP middleware does not wrap WebSocket handshakes; configure Host/Origin policy through
`rapidy.security.WebSocketSecurityConfig`, especially when credentials come from cookies.

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
name/id, and retry metadata. It never sets `Content-Length`. CR, LF, and CRLF inside event data are normalized into
separate `data:` lines, so untrusted content cannot create SSE fields or a second event. Event names and IDs reject CR
or LF; IDs also reject NUL. `retry` must be a non-negative integer.

## Generic streaming

Return `StreamResponse(async_iterable, content_type=...)` for incremental bytes or text. For imperative streaming,
return a response whose handler or downstream code uses `prepare(request)`, `write(bytes)`, then `write_eof()`.
Client disconnect closes the async iterable and request-scoped DI finalizers still run.

All three examples are combined in
[`examples/realtime.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/realtime.py).
