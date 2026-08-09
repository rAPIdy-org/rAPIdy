from __future__ import annotations

import asyncio

from rapidy import Rapidy
from rapidy.http import WebSocket, websocket


@websocket('/push')
async def push(web_socket: WebSocket) -> None:
    await web_socket.accept()
    await web_socket.receive_text()
    payload = b'x' * (256 * 1024)
    while True:
        await web_socket.send_bytes(payload)
        await asyncio.sleep(0)


app = Rapidy(http_route_handlers=[push])
