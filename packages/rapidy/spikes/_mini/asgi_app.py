from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from spikes._mini.request_proto import Request

Send = Callable[[dict[str, Any]], Awaitable[None]]
Handler = Callable[[Request, Send], Awaitable[None]]


async def send_response(
    send: Send,
    status: int,
    body: bytes = b"",
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    response_headers = list(headers or ())
    if not any(name.lower() == b"content-length" for name, _ in response_headers):
        response_headers.append((b"content-length", str(len(body)).encode("ascii")))
    await send(
        {"type": "http.response.start", "status": status, "headers": response_headers}
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


class MiniApp:
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], Handler] = {}

    def add_route(self, method: str, path: str, handler: Handler) -> None:
        self._routes[(method.upper(), path)] = handler

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Send) -> None:
        scope_type = scope["type"]
        if scope_type == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope_type != "http":
            raise RuntimeError(f"Unsupported scope: {scope_type}")

        request = Request(scope, receive)
        handler = self._routes.get((request.method, request.path))
        if handler is None:
            await send_response(send, 404, b"not found")
            return
        await handler(request, send)

    async def _lifespan(self, receive: Any, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return


__all__ = ("Handler", "MiniApp", "Send", "send_response")
