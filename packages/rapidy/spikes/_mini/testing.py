from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class CountingReceive:
    def __init__(self, messages: Iterable[dict[str, Any]]) -> None:
        self._messages = iter(messages)
        self.calls = 0

    async def __call__(self) -> dict[str, Any]:
        self.calls += 1
        try:
            return next(self._messages)
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}


def make_scope(
    method: str = "GET",
    path: str = "/",
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
) -> dict[str, Any]:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "root_path": "",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 80),
    }


async def asgi_call(
    app: Any,
    scope: dict[str, Any],
    receive: Any,
) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    messages: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(scope, receive, send)
    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), list(start.get("headers", [])), body


__all__ = ("CountingReceive", "asgi_call", "make_scope")
