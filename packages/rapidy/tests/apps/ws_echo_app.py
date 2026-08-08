from rapidy import Rapidy
from rapidy.http import Header, PathParam, WebSocket, websocket


@websocket('/ws/{room}')
async def echo(
    ws: WebSocket,
    room: str = PathParam(),
    x_token: str = Header(alias='X-Token'),
) -> None:
    assert room
    assert x_token
    await ws.accept()
    async for message in ws:
        if isinstance(message, str):
            await ws.send_text(message)
        else:
            await ws.send_bytes(message)

@websocket('/json')
async def json_echo(ws: WebSocket) -> None:
    await ws.accept()
    await ws.send_json(await ws.receive_json())


app = Rapidy(http_route_handlers=[echo, json_echo])
