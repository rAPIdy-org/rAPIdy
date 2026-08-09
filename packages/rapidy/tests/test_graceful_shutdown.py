from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import websockets

import pytest
from websockets.exceptions import ConnectionClosed

from rapidy import Rapidy
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.http import get, HTTPRouter, StreamResponse, WebSocket, websocket
from tests.live_server import live_server_process


class QueueTransport:
    def __init__(self) -> None:
        self.incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.sent: list[dict[str, Any]] = []
        self.changed = asyncio.Event()

    def feed(self, message: dict[str, Any]) -> None:
        self.incoming.put_nowait(message)

    async def receive(self) -> dict[str, Any]:
        return await self.incoming.get()

    async def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)
        self.changed.set()

    async def wait_for(self, message_type: str) -> dict[str, Any]:
        while True:
            for message in self.sent:
                if message.get('type') == message_type:
                    return message
            self.changed.clear()
            await self.changed.wait()


class LifespanDriver:
    def __init__(self, app: Rapidy) -> None:
        self.app = app
        self.transport = QueueTransport()
        self.task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.task = asyncio.create_task(
            self.app({'type': 'lifespan'}, self.transport.receive, self.transport.send)
        )
        self.transport.feed({'type': 'lifespan.startup'})
        await self.transport.wait_for('lifespan.startup.complete')

    async def shutdown(self) -> None:
        assert self.task is not None
        self.transport.feed({'type': 'lifespan.shutdown'})
        await self.transport.wait_for('lifespan.shutdown.complete')
        await self.task


def websocket_scope(path: str) -> dict[str, Any]:
    return {
        'type': 'websocket',
        'path': path,
        'query_string': b'',
        'headers': [],
        'subprotocols': [],
        'state': {},
    }


class SessionResource:
    pass


class SessionProvider(Provider):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    @provide(scope=Scope.SESSION)
    async def resource(self) -> AsyncIterator[SessionResource]:
        self.events.append('session_created')
        try:
            yield SessionResource()
        finally:
            self.events.append('session_finalized')


@pytest.mark.asyncio
async def test_open_ws_receives_1001_before_shutdown_hooks() -> None:
    events: list[str] = []
    handler_entered = asyncio.Event()

    @asynccontextmanager
    async def context(_app: Rapidy) -> AsyncIterator[None]:
        yield
        events.append('ctx_exit')

    async def on_shutdown() -> None:
        events.append('on_shutdown')

    async def on_cleanup() -> None:
        events.append('on_cleanup')

    @websocket('/ws')
    async def handler(ws: WebSocket, resource: FromDI[SessionResource]) -> None:
        assert isinstance(resource, SessionResource)
        await ws.accept()
        handler_entered.set()
        await ws.receive_text()

    app = Rapidy(
        di_providers=[SessionProvider(events)],
        http_route_handlers=[handler],
        lifespan=[context],
        on_shutdown=[on_shutdown],
        on_cleanup=[on_cleanup],
    )
    driver = LifespanDriver(app)
    await driver.start()

    ws_transport = QueueTransport()
    ws_transport.feed({'type': 'websocket.connect'})

    async def send(message: dict[str, Any]) -> None:
        await ws_transport.send(message)
        if message.get('type') == 'websocket.close' and message.get('code') == 1001:
            events.append('ws_closed_1001')

    ws_task = asyncio.create_task(app(websocket_scope('/ws'), ws_transport.receive, send))
    await handler_entered.wait()
    await asyncio.sleep(0)
    assert len(app.state._open_websockets) == 1

    await driver.shutdown()
    close = next(message for message in ws_transport.sent if message.get('type') == 'websocket.close')
    assert close['code'] == 1001
    assert events.index('ws_closed_1001') < events.index('on_shutdown') < events.index('on_cleanup')
    assert events.index('on_cleanup') < events.index('ctx_exit')

    ws_transport.feed({'type': 'websocket.disconnect', 'code': 1001})
    await ws_task
    assert events.count('session_finalized') == 1
    assert app.state._open_websockets == set()


@pytest.mark.asyncio
@pytest.mark.parametrize('outcome', ['normal', 'disconnect', 'exception'])
async def test_registry_cleanup_all_connection_outcomes(outcome: str) -> None:
    @websocket('/ws')
    async def handler(ws: WebSocket) -> None:
        await ws.accept()
        if outcome == 'normal':
            await ws.close()
        elif outcome == 'disconnect':
            await ws.receive_text()
        else:
            msg = 'boom'
            raise RuntimeError(msg)

    app = Rapidy(http_route_handlers=[handler])
    transport = QueueTransport()
    transport.feed({'type': 'websocket.connect'})
    if outcome == 'disconnect':
        transport.feed({'type': 'websocket.disconnect', 'code': 1000})

    async with app.lifespan.ctx_manager():
        await app(websocket_scope('/ws'), transport.receive, transport.send)
        assert app.state._open_websockets == set()


@pytest.mark.asyncio
async def test_subapp_websocket_uses_root_registry_and_closes_1001() -> None:
    entered = asyncio.Event()

    @websocket('/ws')
    async def handler(ws: WebSocket) -> None:
        await ws.accept()
        entered.set()
        await ws.receive_text()

    router = HTTPRouter('/v1', [handler])
    app = Rapidy(http_route_handlers=[router])
    driver = LifespanDriver(app)
    await driver.start()
    transport = QueueTransport()
    transport.feed({'type': 'websocket.connect'})
    task = asyncio.create_task(app(websocket_scope('/v1/ws'), transport.receive, transport.send))
    await entered.wait()
    await asyncio.sleep(0)

    assert len(app.state._open_websockets) == 1
    assert router.application.state._open_websockets == set()
    await driver.shutdown()
    assert any(message.get('code') == 1001 for message in transport.sent)

    transport.feed({'type': 'websocket.disconnect', 'code': 1001})
    await task
    assert app.state._open_websockets == set()


@pytest.mark.asyncio
async def test_http_stream_finishes_during_shutdown() -> None:
    release = asyncio.Event()

    @get('/stream')
    async def handler() -> StreamResponse:
        async def chunks() -> AsyncIterator[bytes]:
            yield b'first'
            await release.wait()
            yield b'second'

        return StreamResponse(body=chunks())

    app = Rapidy(http_route_handlers=[handler])
    driver = LifespanDriver(app)
    await driver.start()
    transport = QueueTransport()
    transport.feed({'type': 'http.request', 'body': b'', 'more_body': False})
    scope: dict[str, Any] = {
        'type': 'http',
        'http_version': '1.1',
        'method': 'GET',
        'path': '/stream',
        'query_string': b'',
        'headers': [],
        'state': {},
    }
    request_task = asyncio.create_task(app(scope, transport.receive, transport.send))
    await transport.wait_for('http.response.body')

    await driver.shutdown()
    assert not request_task.done()
    release.set()
    await request_task

    assert [message.get('body') for message in transport.sent[1:]] == [b'first', b'second', b'']
    assert transport.sent[-1]['more_body'] is False


@pytest.mark.asyncio
async def test_race_client_disconnect_vs_shutdown_finalizes_once() -> None:
    events: list[str] = []
    entered = asyncio.Event()

    @websocket('/ws')
    async def handler(ws: WebSocket, resource: FromDI[SessionResource]) -> None:
        assert isinstance(resource, SessionResource)
        await ws.accept()
        entered.set()
        await ws.receive_text()

    app = Rapidy(
        di_providers=[SessionProvider(events)],
        http_route_handlers=[handler],
    )
    driver = LifespanDriver(app)
    await driver.start()
    transport = QueueTransport()
    transport.feed({'type': 'websocket.connect'})
    ws_task = asyncio.create_task(app(websocket_scope('/ws'), transport.receive, transport.send))
    await entered.wait()
    await asyncio.sleep(0)

    transport.feed({'type': 'websocket.disconnect', 'code': 1000})
    await asyncio.gather(driver.shutdown(), ws_task)

    close_frames = [message for message in transport.sent if message.get('type') == 'websocket.close']
    assert len(close_frames) <= 1
    assert events.count('session_finalized') == 1
    assert app.state._open_websockets == set()


@pytest.mark.asyncio
async def test_lifespan_without_websockets_preserves_order() -> None:
    events: list[str] = []

    @asynccontextmanager
    async def context(_app: Rapidy) -> AsyncIterator[None]:
        events.append('ctx_enter')
        try:
            yield
        finally:
            events.append('ctx_exit')

    async def on_startup() -> None:
        events.append('startup')

    async def on_shutdown() -> None:
        events.append('shutdown')

    async def on_cleanup() -> None:
        events.append('cleanup')

    app = Rapidy(
        lifespan=[context],
        on_startup=[on_startup],
        on_shutdown=[on_shutdown],
        on_cleanup=[on_cleanup],
    )
    driver = LifespanDriver(app)
    await driver.start()
    events.append('work')
    await driver.shutdown()
    assert events == ['ctx_enter', 'startup', 'work', 'shutdown', 'cleanup', 'ctx_exit']


def _read_process_output(process) -> str:
    assert process.stdout is not None
    return process.stdout.read().decode(errors='replace')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'runtime',
    [
        pytest.param(
            'granian',
            marks=pytest.mark.xfail(
                strict=True,
                reason='Granian 2.8.1 drops accepted WebSockets without a close frame on SIGTERM',
            ),
        ),
        'uvicorn',
    ],
)
async def test_live_server_shutdown_closes_an_accepted_websocket(runtime: str) -> None:
    with live_server_process(runtime, 'examples.realtime:app') as server:
        uri = server.base_url.replace('http://', 'ws://') + '/ws'
        async with websockets.connect(uri) as client:
            await client.send('accepted')
            assert await client.recv() == 'accepted'
            server.process.terminate()
            with pytest.raises(ConnectionClosed):
                await asyncio.wait_for(client.recv(), timeout=10)
            close_code = client.close_code
        await asyncio.to_thread(server.process.wait, 10)
        output = await asyncio.to_thread(_read_process_output, server.process)

    assert close_code in {1001, 1012}, output


@pytest.mark.asyncio
@pytest.mark.parametrize('runtime', ['granian', 'uvicorn'])
async def test_live_peer_abort_during_send_has_no_framework_traceback(runtime: str) -> None:
    with live_server_process(runtime, 'tests.apps.ws_lifecycle_app:app') as server:
        uri = server.base_url.replace('http://', 'ws://') + '/push'
        client = await websockets.connect(uri, max_size=None)
        await client.send('start')
        assert await client.recv() == b'x' * (256 * 1024)
        client.transport.abort()
        await asyncio.sleep(0.5)
        server.process.terminate()
        await asyncio.to_thread(server.process.wait, 10)
        output = await asyncio.to_thread(_read_process_output, server.process)

    assert 'Unhandled exception during WebSocket processing' not in output
