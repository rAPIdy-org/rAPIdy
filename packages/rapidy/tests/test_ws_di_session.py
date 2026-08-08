from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from rapidy import Rapidy
from rapidy.depends import AsyncContainer, FromDI, provide, Provider, Scope
from rapidy.http import HTTPRouter, Request, WebSocket, websocket


class SessionResource:
    pass


class AppResource:
    pass


class WebSocketResourceProvider(Provider):
    def __init__(self, events: list[str], context_objects: list[tuple[WebSocket, Request]]) -> None:
        super().__init__()
        self.events = events
        self.context_objects = context_objects

    @provide(scope=Scope.SESSION)
    async def session_resource(self, ws: WebSocket, request: Request) -> AsyncIterator[SessionResource]:
        self.events.append('session_created')
        self.context_objects.append((ws, request))
        try:
            yield SessionResource()
        finally:
            self.events.append('session_finalized')

    @provide(scope=Scope.APP)
    def app_resource(self) -> AppResource:
        self.events.append('app_created')
        return AppResource()


class Transport:
    def __init__(self, incoming: list[dict[str, Any]]) -> None:
        self._incoming = iter(incoming)
        self.sent: list[dict[str, Any]] = []

    async def receive(self) -> dict[str, Any]:
        try:
            return next(self._incoming)
        except StopIteration:
            msg = 'Unexpected WebSocket receive'
            raise AssertionError(msg) from None

    async def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)


async def dispatch(
    app: Rapidy,
    path: str,
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    transport = Transport(incoming)
    scope: dict[str, Any] = {
        'type': 'websocket',
        'path': path,
        'query_string': b'',
        'headers': [],
        'subprotocols': [],
        'state': {},
    }
    await app(scope, transport.receive, transport.send)
    return transport.sent


def create_provider() -> tuple[WebSocketResourceProvider, list[str], list[tuple[WebSocket, Request]]]:
    events: list[str] = []
    context_objects: list[tuple[WebSocket, Request]] = []
    return WebSocketResourceProvider(events, context_objects), events, context_objects


@pytest.mark.asyncio
async def test_session_finalizer_once_on_normal_close() -> None:
    provider, events, _context_objects = create_provider()

    @websocket('/ws')
    async def handler(ws: WebSocket, resource: FromDI[SessionResource]) -> None:
        assert isinstance(resource, SessionResource)
        events.append('handler')
        await ws.accept()
        await ws.close()

    app = Rapidy(di_providers=[provider], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        sent = await dispatch(app, '/ws', [{'type': 'websocket.connect'}])

    assert sent[-1] == {'type': 'websocket.close', 'code': 1000, 'reason': ''}
    assert events == ['session_created', 'handler', 'session_finalized']


@pytest.mark.asyncio
async def test_session_finalizer_once_on_client_disconnect() -> None:
    provider, events, _context_objects = create_provider()

    @websocket('/ws')
    async def handler(ws: WebSocket, resource: FromDI[SessionResource]) -> None:
        assert isinstance(resource, SessionResource)
        events.append('handler')
        await ws.accept()
        await ws.receive_text()

    app = Rapidy(di_providers=[provider], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        sent = await dispatch(
            app,
            '/ws',
            [
                {'type': 'websocket.connect'},
                {'type': 'websocket.disconnect', 'code': 1001},
            ],
        )

    assert sent == [{'type': 'websocket.accept', 'subprotocol': None, 'headers': []}]
    assert events == ['session_created', 'handler', 'session_finalized']


@pytest.mark.asyncio
async def test_session_finalizer_once_on_handler_exception() -> None:
    provider, events, _context_objects = create_provider()

    @websocket('/ws')
    async def handler(ws: WebSocket, resource: FromDI[SessionResource]) -> None:
        assert isinstance(resource, SessionResource)
        events.append('handler')
        await ws.accept()
        msg = 'boom'
        raise RuntimeError(msg)

    app = Rapidy(di_providers=[provider], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        sent = await dispatch(app, '/ws', [{'type': 'websocket.connect'}])

    assert sent[-1] == {'type': 'websocket.close', 'code': 1011, 'reason': ''}
    assert events == ['session_created', 'handler', 'session_finalized']


@pytest.mark.asyncio
async def test_web_socket_and_request_bindings_use_connection_objects() -> None:
    provider, _events, context_objects = create_provider()
    handler_objects: list[tuple[WebSocket, Request]] = []

    @websocket('/ws')
    async def handler(
        connection: WebSocket,
        request: Request,
        resource: FromDI[SessionResource],
    ) -> None:
        assert isinstance(resource, SessionResource)
        handler_objects.append((connection, request))
        await connection.accept()
        await connection.close()

    app = Rapidy(di_providers=[provider], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        await dispatch(app, '/ws', [{'type': 'websocket.connect'}])

    assert len(context_objects) == len(handler_objects) == 1
    assert context_objects[0][0] is handler_objects[0][0]
    assert context_objects[0][1] is handler_objects[0][1]
    assert context_objects[0][1].method == 'GET'


@pytest.mark.asyncio
async def test_app_singleton_survives_ws_connections() -> None:
    provider, events, _context_objects = create_provider()
    instances: list[AppResource] = []

    @websocket('/ws')
    async def handler(
        ws: WebSocket,
        session: FromDI[SessionResource],
        singleton: FromDI[AppResource],
    ) -> None:
        assert isinstance(session, SessionResource)
        instances.append(singleton)
        await ws.accept()
        await ws.close()

    app = Rapidy(di_providers=[provider], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        await dispatch(app, '/ws', [{'type': 'websocket.connect'}])
        await dispatch(app, '/ws', [{'type': 'websocket.connect'}])

    assert instances[0] is instances[1]
    assert events.count('app_created') == 1
    assert events.count('session_finalized') == 2


@pytest.mark.asyncio
async def test_ws_in_subapp_uses_root_container() -> None:
    provider, events, _context_objects = create_provider()

    @websocket('/ws')
    async def handler(ws: WebSocket, resource: FromDI[SessionResource]) -> None:
        assert isinstance(resource, SessionResource)
        await ws.accept()
        await ws.close()

    router = HTTPRouter('/v1', [handler])
    app = Rapidy(di_providers=[provider], http_route_handlers=[router])
    async with app.lifespan.ctx_manager():
        assert isinstance(app.di_container, AsyncContainer)
        assert router.application.di_container is None
        sent = await dispatch(app, '/v1/ws', [{'type': 'websocket.connect'}])

    assert sent[-1]['type'] == 'websocket.close'
    assert events.count('session_finalized') == 1
