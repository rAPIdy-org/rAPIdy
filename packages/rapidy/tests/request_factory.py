from __future__ import annotations

from typing import Any

from rapidy import Rapidy
from rapidy.request import Request


class ReceiveMock:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = messages
        self.calls = 0

    async def __call__(self) -> dict[str, Any]:
        if self.calls >= len(self.messages):
            msg = 'receive called after more_body=False'
            raise AssertionError(msg)
        message = self.messages[self.calls]
        self.calls += 1
        return message


def make_request(
    *,
    method: str = 'GET',
    path: str = '/',
    headers: tuple[tuple[bytes, bytes], ...] = (),
    query_string: bytes = b'',
    body_chunks: list[bytes] | None = None,
    messages: list[dict[str, Any]] | None = None,
    http_version: str = '1.1',
    app: Rapidy | None = None,
) -> tuple[Request, ReceiveMock]:
    if messages is None:
        chunks = body_chunks if body_chunks is not None else [b'']
        messages = [
            {
                'type': 'http.request',
                'body': chunk,
                'more_body': index < len(chunks) - 1,
            }
            for index, chunk in enumerate(chunks)
        ]

    receive = ReceiveMock(messages)
    scope: dict[str, Any] = {
        'type': 'http',
        'http_version': http_version,
        'method': method,
        'path': path,
        'query_string': query_string,
        'headers': list(headers),
        'state': {},
        'app': app if app is not None else Rapidy(),
    }
    return Request(scope, receive), receive
