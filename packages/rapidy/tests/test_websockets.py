from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import websockets as ws_client

import httpx
import pytest

from rapidy import Rapidy
from rapidy.exceptions import HTTPNotFound
from rapidy.http import (
    Body,
    Cookie,
    get,
    Header,
    HTTPRouter,
    PathParam,
    QueryParam,
    Request,
    WebSocket,
    websocket,
    WebSocketDisconnect,
)
from rapidy.routing.http.base import IncorrectPathError
from rapidy.routing.http.routers import (
    BodyNotAvailableInWebSocketHandlerError,
    HandlerIsNotAsyncFuncTypeError,
    MissingPathError,
    WebSocketFieldAlreadyExistsError,
)
from rapidy.routing.matcher import DuplicateRouteError, UrlMatcher
from rapidy.websockets import (
    WebSocketClosedError,
    WebSocketFrameTypeError,
    WebSocketNotAcceptedError,
    WebSocketState,
)
from tests.live_server import live_server


class FakeWSTransport:
    def __init__(self, incoming: list[dict[str, Any]]) -> None:
        self.incoming = iter(incoming)
        self.sent: list[dict[str, Any]] = []

    async def receive(self) -> dict[str, Any]:
        try:
            return next(self.incoming)
        except StopIteration:
            msg = 'WebSocket receive called after the prepared messages were exhausted'
            raise AssertionError(msg) from None

    async def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)


def ws_scope(
    path: str = '/ws',
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b'',
) -> dict[str, Any]:
    return {
        'type': 'websocket',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'scheme': 'ws',
        'path': path,
        'raw_path': path.encode(),
        'query_string': query_string,
        'headers': headers or [],
        'client': ('127.0.0.1', 50000),
        'server': ('127.0.0.1', 8000),
        'subprotocols': ['chat'],
        'state': {},
    }


async def run_ws(
    app: Rapidy,
    path: str,
    incoming: list[dict[str, Any]],
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b'',
) -> list[dict[str, Any]]:
    transport = FakeWSTransport(incoming)
    async with app.lifespan.ctx_manager():
        await app(ws_scope(path, headers=headers, query_string=query_string), transport.receive, transport.send)
    return transport.sent


@pytest.mark.asyncio
async def test_accept_consumes_connect_and_sends_accept() -> None:
    transport = FakeWSTransport([{'type': 'websocket.connect'}])
    ws = WebSocket(ws_scope(headers=[(b'x-one', b'1')]), transport.receive, transport.send)

    assert ws.path == '/ws'
    assert ws.headers['x-one'] == '1'
    assert ws.query_string == ''
    assert ws.subprotocols == ['chat']
    await ws.accept(subprotocol='chat', headers={'x-accepted': 'yes'})
    await ws.accept()

    assert ws.client_state is WebSocketState.CONNECTED
    assert ws.application_state is WebSocketState.CONNECTED
    assert transport.sent == [
        {
            'type': 'websocket.accept',
            'subprotocol': 'chat',
            'headers': [(b'x-accepted', b'yes')],
        }
    ]


@pytest.mark.asyncio
async def test_receive_and_send_typed_frames() -> None:
    transport = FakeWSTransport(
        [
            {'type': 'websocket.connect'},
            {'type': 'websocket.receive', 'text': 'hello'},
            {'type': 'websocket.receive', 'bytes': b'raw'},
            {'type': 'websocket.receive', 'text': 'json:7'},
        ]
    )
    ws = WebSocket(ws_scope(), transport.receive, transport.send)
    await ws.accept()

    assert await ws.receive_text() == 'hello'
    assert await ws.receive_bytes() == b'raw'
    assert await ws.receive_json(loads=lambda value: int(value.removeprefix('json:'))) == 7
    await ws.send_text('world')
    await ws.send_bytes(b'data')
    await ws.send_json({'ok': True}, dumps=lambda value: f'encoded:{value["ok"]}')

    assert transport.sent[1:] == [
        {'type': 'websocket.send', 'text': 'world'},
        {'type': 'websocket.send', 'bytes': b'data'},
        {'type': 'websocket.send', 'text': 'encoded:True'},
    ]


@pytest.mark.asyncio
async def test_frame_state_errors_and_idempotent_close() -> None:
    transport = FakeWSTransport(
        [
            {'type': 'websocket.connect'},
            {'type': 'websocket.receive', 'bytes': b'raw'},
            {'type': 'websocket.receive', 'text': 'text'},
        ]
    )
    ws = WebSocket(ws_scope(), transport.receive, transport.send)

    with pytest.raises(WebSocketNotAcceptedError):
        await ws.receive_text()
    await ws.accept()
    with pytest.raises(WebSocketFrameTypeError):
        await ws.receive_text()
    with pytest.raises(WebSocketFrameTypeError):
        await ws.receive_bytes()
    await ws.close(code=1001, reason='done')
    await ws.close()
    with pytest.raises(WebSocketClosedError):
        await ws.send_text('late')

    assert transport.sent[-1] == {'type': 'websocket.close', 'code': 1001, 'reason': 'done'}
    assert sum(message['type'] == 'websocket.close' for message in transport.sent) == 1


@pytest.mark.asyncio
async def test_disconnect_and_async_iteration() -> None:
    direct = FakeWSTransport(
        [
            {'type': 'websocket.connect'},
            {'type': 'websocket.disconnect', 'code': 1001, 'reason': 'bye'},
        ]
    )
    ws = WebSocket(ws_scope(), direct.receive, direct.send)
    await ws.accept()
    with pytest.raises(WebSocketDisconnect) as captured:
        await ws.receive_text()
    assert (captured.value.code, captured.value.reason) == (1001, 'bye')
    assert ws.client_state is ws.application_state is WebSocketState.DISCONNECTED

    iteration = FakeWSTransport(
        [
            {'type': 'websocket.connect'},
            {'type': 'websocket.receive', 'text': 'one'},
            {'type': 'websocket.receive', 'bytes': b'two'},
            {'type': 'websocket.disconnect', 'code': 1000},
        ]
    )
    iterable = WebSocket(ws_scope(), iteration.receive, iteration.send)
    await iterable.accept()
    assert [message async for message in iterable] == ['one', b'two']


@pytest.mark.asyncio
async def test_close_rejects_without_accept() -> None:
    transport = FakeWSTransport([{'type': 'websocket.connect'}])
    ws = WebSocket(ws_scope(), transport.receive, transport.send)
    await ws.close(code=1000)
    assert ws.client_state is WebSocketState.CONNECTED
    assert ws.application_state is WebSocketState.DISCONNECTED
    assert transport.sent == [{'type': 'websocket.close', 'code': 1000, 'reason': ''}]


def test_no_circular_imports_from_websocket_transport() -> None:
    source_path = inspect.getsourcefile(WebSocket)
    assert source_path is not None
    tree = ast.parse(Path(source_path).read_text())
    modules = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    modules.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    assert not any(
        module == 'rapidy' or module.startswith(('rapidy.depends', 'rapidy.di', 'rapidy.application'))
        for module in modules
    )


async def ws_terminal(*_args: Any) -> None:
    return None


def test_ws_matcher_contract() -> None:
    matcher = UrlMatcher()
    matcher.add_ws_route('/ws/{room}', ws_terminal)
    matcher.add_ws_route('/api/{version:\\d+}/ws', ws_terminal)

    assert matcher.resolve_ws('/ws/lobby').path_params == {'room': 'lobby'}
    assert matcher.resolve_ws('/api/1/ws').path_params == {'version': '1'}
    with pytest.raises(HTTPNotFound):
        matcher.resolve_ws('/api/v1/ws')
    with pytest.raises(DuplicateRouteError):
        matcher.add_ws_route('/ws/{room}', ws_terminal)


def test_ws_matcher_static_priority_and_http_independence() -> None:
    async def dynamic(*_args: Any) -> None:
        return None

    async def static(*_args: Any) -> None:
        return None

    async def http_terminal(*_args: Any) -> Any:
        return None

    matcher = UrlMatcher()
    matcher.add_ws_route('/ws/{room}', dynamic)
    matcher.add_ws_route('/ws/lobby', static)
    matcher.add_route('GET', '/ws/{room}', http_terminal, {})

    assert matcher.resolve_ws('/ws/lobby').terminal is static
    assert matcher.resolve_ws('/ws/other').terminal is dynamic
    assert matcher.resolve('GET', '/ws/lobby').terminal is http_terminal


def test_websocket_registration_errors() -> None:
    def sync_handler() -> None:
        return None

    with pytest.raises(HandlerIsNotAsyncFuncTypeError):
        websocket('/ws')(sync_handler)  # type: ignore[arg-type]
    with pytest.raises(IncorrectPathError):
        websocket('ws')

    @websocket()
    async def missing_path() -> None:
        return None

    with pytest.raises(MissingPathError):
        Rapidy(http_route_handlers=[missing_path])

    @websocket('/body')
    async def body_handler(data: dict[str, Any] = Body()) -> None:
        return None

    with pytest.raises(BodyNotAvailableInWebSocketHandlerError):
        Rapidy(http_route_handlers=[body_handler])

    @websocket('/double')
    async def duplicate_ws(first: WebSocket, second: WebSocket) -> None:
        return None

    with pytest.raises(WebSocketFieldAlreadyExistsError):
        Rapidy(http_route_handlers=[duplicate_ws])


@pytest.mark.asyncio
async def test_ws_echo_asgi_with_path_and_header_extraction() -> None:
    seen: list[tuple[str, str]] = []

    @websocket('/ws/{room}')
    async def echo_handler(
        connection: WebSocket,
        room: str = PathParam(),
        x_token: str = Header(alias='X-Token'),
    ) -> None:
        seen.append((room, x_token))
        await connection.accept()
        async for message in connection:
            if isinstance(message, str):
                await connection.send_text(message)
            else:
                await connection.send_bytes(message)

    sent = await run_ws(
        Rapidy(http_route_handlers=[echo_handler]),
        '/ws/lobby',
        [
            {'type': 'websocket.connect'},
            {'type': 'websocket.receive', 'text': 'hi'},
            {'type': 'websocket.disconnect', 'code': 1000},
        ],
        headers=[(b'x-token', b'secret')],
    )

    assert seen == [('lobby', 'secret')]
    assert sent[0]['type'] == 'websocket.accept'
    assert sent[1] == {'type': 'websocket.send', 'text': 'hi'}


@pytest.mark.asyncio
async def test_ws_not_found_and_invalid_params_reject_handshake() -> None:
    @websocket('/required')
    async def required(connection: WebSocket, token: str = QueryParam()) -> None:
        await connection.accept()

    app = Rapidy(http_route_handlers=[required])
    not_found = await run_ws(app, '/missing', [{'type': 'websocket.connect'}])
    invalid = await run_ws(app, '/required', [{'type': 'websocket.connect'}])

    assert not_found == [{'type': 'websocket.close', 'code': 1000}]
    assert invalid == [{'type': 'websocket.close', 'code': 1000, 'reason': ''}]
    assert all(message['type'] != 'websocket.accept' for message in [*not_found, *invalid])


@pytest.mark.asyncio
async def test_ws_query_cookie_and_request_injection() -> None:
    seen: list[tuple[int, str, str, bool]] = []

    @websocket('/extract')
    async def handler(
        socket: WebSocket,
        request: Request,
        page: int = QueryParam(),
        session: str = Cookie(),
    ) -> None:
        seen.append((page, session, request.method, isinstance(request, Request)))
        await socket.accept()
        await socket.close()

    app = Rapidy(http_route_handlers=[handler])
    sent = await run_ws(
        app,
        '/extract',
        [{'type': 'websocket.connect'}],
        headers=[(b'cookie', b'session=abc')],
        query_string=b'page=2',
    )

    assert seen == [(2, 'abc', 'GET', True)]
    assert sent[-1] == {'type': 'websocket.close', 'code': 1000, 'reason': ''}


@pytest.mark.asyncio
async def test_ws_mount_static_regex_and_http_stack() -> None:
    @websocket('/ws/{room}')
    async def dynamic(connection: WebSocket) -> None:
        await connection.accept()
        await connection.send_text('dynamic')
        await connection.close()

    @websocket('/ws/lobby')
    async def static(connection: WebSocket) -> None:
        await connection.accept()
        await connection.send_text('static')
        await connection.close()

    @websocket('/version/{value:\\d+}')
    async def regex(connection: WebSocket, value: int = PathParam()) -> None:
        await connection.accept()
        await connection.send_text(str(value))
        await connection.close()

    @get('/ping')
    async def ping() -> str:
        return 'pong'

    router = HTTPRouter('/v1', [dynamic, static, regex, ping])
    app = Rapidy(http_route_handlers=[router])
    static_sent = await run_ws(app, '/v1/ws/lobby', [{'type': 'websocket.connect'}])
    regex_sent = await run_ws(app, '/v1/version/7', [{'type': 'websocket.connect'}])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/v1/ping')

    assert static_sent[1] == {'type': 'websocket.send', 'text': 'static'}
    assert regex_sent[1] == {'type': 'websocket.send', 'text': '7'}
    assert response.status_code == 200
    assert response.text == 'pong'


@pytest.mark.asyncio
async def test_ws_dispatch_closes_on_exit_disconnect_and_exception() -> None:
    @websocket('/exit')
    async def exits(connection: WebSocket) -> None:
        await connection.accept()

    @websocket('/disconnect')
    async def disconnects(connection: WebSocket) -> None:
        await connection.accept()
        await connection.receive_text()

    @websocket('/error')
    async def errors(connection: WebSocket) -> None:
        await connection.accept()
        msg = 'boom'
        raise RuntimeError(msg)

    app = Rapidy(http_route_handlers=[exits, disconnects, errors])
    exited = await run_ws(app, '/exit', [{'type': 'websocket.connect'}])
    disconnected = await run_ws(
        app,
        '/disconnect',
        [
            {'type': 'websocket.connect'},
            {'type': 'websocket.disconnect', 'code': 1001},
        ],
    )
    failed = await run_ws(app, '/error', [{'type': 'websocket.connect'}])

    assert exited[-1] == {'type': 'websocket.close', 'code': 1000, 'reason': ''}
    assert disconnected == [{'type': 'websocket.accept', 'subprotocol': None, 'headers': []}]
    assert failed[-1] == {'type': 'websocket.close', 'code': 1011, 'reason': ''}


async def assert_live_echo(runtime: str) -> None:
    with live_server(runtime, 'tests.apps.ws_echo_app:app') as base_url:
        uri = base_url.replace('http://', 'ws://') + '/ws/lobby'
        async with ws_client.connect(uri, additional_headers={'X-Token': 'secret'}) as client:
            await client.send('hi')
            assert await client.recv() == 'hi'
            await client.send(b'raw')
            assert await client.recv() == b'raw'


@pytest.mark.asyncio
async def test_ws_echo_granian() -> None:
    await assert_live_echo('granian')
    with live_server('granian', 'tests.apps.ws_echo_app:app') as base_url:
        uri = base_url.replace('http://', 'ws://') + '/json'
        async with ws_client.connect(uri) as client:
            await client.send(json.dumps({'answer': 42}))
            assert json.loads(await client.recv()) == {'answer': 42}


@pytest.mark.asyncio
async def test_ws_echo_uvicorn() -> None:
    await assert_live_echo('uvicorn')


def test_public_ws_contract() -> None:
    from rapidy import http  # noqa: PLC0415
    from rapidy.depends import RapidyProvider  # noqa: PLC0415

    assert {'websocket', 'WebSocket', 'WebSocketDisconnect', 'StreamResponse', 'SSEResponse'} <= set(http.__all__)
    assert len(http.__all__) == 90
    assert hasattr(RapidyProvider, 'web_socket')
    assert 'web_socket' not in __import__('rapidy.depends', fromlist=['__all__']).__all__
    assert list(inspect.signature(WebSocket.accept).parameters) == ['self', 'subprotocol', 'headers']
    assert list(inspect.signature(WebSocket.close).parameters) == ['self', 'code', 'reason']
