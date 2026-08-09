from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from rapidy import Rapidy
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.http import Cookie, get, Header, HTTPFound, SSEResponse, WebSocket, websocket
from rapidy.responses import SSEEvent
from rapidy.testing import AsyncTestClient, create_async_test_client, create_test_client, TestClient


def test_testing_module_reports_missing_optional_dependencies() -> None:
    package_root = Path(__file__).resolve().parents[1]
    code = r"""
import importlib.abc
import sys

sys.path.insert(0, sys.argv[1])

class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.partition('.')[0]
        if root in {'anyio', 'httpx'}:
            raise ModuleNotFoundError('blocked optional dependency', name=root)
        return None

sys.meta_path.insert(0, BlockOptional())
import rapidy.testing as testing
assert 'TestClient' in dir(testing)
try:
    testing.TestClient
except testing.MissingTestingDependencyError as exc:
    assert "pip install rapidy[test]" in str(exc)
else:
    raise AssertionError('missing typed optional-dependency error')
"""
    result = subprocess.run(  # noqa: S603 - fixed interpreter and inline fixture
        [sys.executable, '-I', '-c', code, str(package_root)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_async_client_owns_lifespan_headers_cookies_and_root_path() -> None:
    events: list[str] = []

    async def startup() -> None:
        events.append('startup')

    async def shutdown() -> None:
        events.append('shutdown')

    async def cleanup() -> None:
        events.append('cleanup')

    @get('/probe')
    async def probe(token: str = Header(alias='X-Token'), session: str = Cookie()) -> dict[str, str]:
        return {'token': token, 'session': session}

    app = Rapidy(
        http_route_handlers=[probe],
        on_startup=[startup],
        on_shutdown=[shutdown],
        on_cleanup=[cleanup],
    )
    async with AsyncTestClient(
        app,
        root_path='/api',
        headers={'X-Token': 'test'},
        cookies={'session': 'cookie'},
    ) as client:
        assert events == ['startup']
        response = await client.get('/api/probe')
        assert response.status_code == 200
        assert response.json() == {'token': 'test', 'session': 'cookie'}

    assert events == ['startup', 'shutdown', 'cleanup']


def test_sync_client_works_with_and_without_lifespan_context() -> None:
    events: list[str] = []

    @get('/')
    async def hello() -> dict[str, bool]:
        return {'started': bool(events)}

    app = Rapidy(http_route_handlers=[hello], on_startup=[lambda: events.append('startup')])
    client = TestClient(app)
    try:
        assert client.get('/').json() == {'started': False}
    finally:
        client.close()

    with TestClient(app) as lifespan_client:
        assert lifespan_client.get('/').json() == {'started': True}


@pytest.mark.asyncio
async def test_server_exception_policy_is_explicit() -> None:
    @get('/')
    async def broken() -> None:
        msg = 'broken handler'
        raise RuntimeError(msg)

    app = Rapidy(http_route_handlers=[broken])
    async with AsyncTestClient(app) as client:
        with pytest.raises(RuntimeError, match='broken handler'):
            await client.get('/')

    async with AsyncTestClient(app, raise_server_exceptions=False) as client:
        response = await client.get('/')
    assert response.status_code == 500
    assert response.text == '500: Internal Server Error'


class Service:
    def __init__(self, value: str) -> None:
        self.value = value


class ProductionProvider(Provider):
    def __init__(self, finalized: list[str]) -> None:
        super().__init__()
        self.finalized = finalized

    @provide(scope=Scope.APP)
    async def service(self) -> AsyncIterator[Service]:
        try:
            yield Service('production')
        finally:
            self.finalized.append('production')


class OverrideProvider(Provider):
    def __init__(self, finalized: list[str]) -> None:
        super().__init__()
        self.finalized = finalized

    @provide(scope=Scope.APP, override=True)
    async def service(self) -> AsyncIterator[Service]:
        try:
            yield Service('testing')
        finally:
            self.finalized.append('testing')


def test_di_provider_override_is_isolated_and_restored() -> None:
    production_finalized: list[str] = []
    override_finalized: list[str] = []

    @get('/')
    async def read_service(service: FromDI[Service]) -> str:
        return service.value

    app = Rapidy(http_route_handlers=[read_service], di_providers=[ProductionProvider(production_finalized)])
    with TestClient(app, di_providers=[OverrideProvider(override_finalized)]) as client:
        assert client.get('/').text == 'testing'
    assert override_finalized == ['testing']
    assert production_finalized == []

    with TestClient(app) as client:
        assert client.get('/').text == 'production'
    assert production_finalized == ['production']


def test_redirect_policy_is_configurable() -> None:
    @get('/start')
    async def start() -> None:
        raise HTTPFound(location='/finish')

    @get('/finish')
    async def finish() -> str:
        return 'done'

    app = Rapidy(http_route_handlers=[start, finish])
    with TestClient(app) as client:
        response = client.get('/start')
        assert response.text == 'done'
        assert [item.status_code for item in response.history] == [302]

    with TestClient(app, follow_redirects=False) as client:
        response = client.get('/start')
        assert response.status_code == 302
        assert response.headers['location'] == '/finish'


def test_nested_clients_for_one_app_are_rejected() -> None:
    app = Rapidy()
    with TestClient(app), pytest.raises(RuntimeError, match='already owns'), TestClient(app):
        pass


def test_failed_startup_releases_application_for_another_client() -> None:
    attempts = 0

    async def startup() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            msg = 'startup failed'
            raise RuntimeError(msg)

    app = Rapidy(on_startup=[startup])
    with pytest.raises(RuntimeError, match='startup failed'), TestClient(app):
        pass

    with TestClient(app):
        assert attempts == 2


@pytest.mark.asyncio
async def test_client_factories_build_small_apps() -> None:
    @get('/')
    async def hello() -> str:
        return 'ok'

    with create_test_client([hello]) as client:
        assert client.get('/').text == 'ok'
        assert client.app.routes

    async with create_async_test_client([hello]) as client:
        assert (await client.get('/')).text == 'ok'
        assert client.app.routes


@pytest.mark.asyncio
async def test_async_websocket_session_supports_frames_subprotocol_and_headers() -> None:
    @websocket('/ws')
    async def echo(socket: WebSocket) -> None:
        await socket.accept(subprotocol='json', headers={'X-Accepted': 'yes'})
        text = await socket.receive_text()
        await socket.send_text(text.upper())
        data = await socket.receive_bytes()
        await socket.send_bytes(data[::-1])

    app = Rapidy(http_route_handlers=[echo])
    async with (
        AsyncTestClient(app) as client,
        client.websocket_connect('/ws', subprotocols=['json']) as session,
    ):
        assert session.accepted_subprotocol == 'json'
        assert session.accepted_headers == ((b'X-Accepted', b'yes'),)
        await session.send_text('hello')
        assert await session.receive_text() == 'HELLO'
        await session.send_bytes(b'abc')
        assert await session.receive_bytes() == b'cba'


def test_sync_websocket_session_and_context_requirement() -> None:
    @websocket('/ws')
    async def echo(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_json(await socket.receive_json())

    app = Rapidy(http_route_handlers=[echo])
    plain_client = TestClient(app)
    with pytest.raises(RuntimeError, match='require'):
        plain_client.websocket_connect('/ws')
    plain_client.close()

    with TestClient(app) as client, client.websocket_connect('/ws') as session:
        session.send_json({'value': 1})
        assert session.receive_json() == {'value': 1}


@pytest.mark.asyncio
async def test_async_sse_session_is_incremental_and_disconnects_stream() -> None:
    closed = asyncio.Event()

    async def events() -> AsyncIterator[SSEEvent]:
        try:
            yield SSEEvent({'value': 1}, event='update', id='one')
            await asyncio.Event().wait()
        finally:
            closed.set()

    @get('/events')
    async def stream_events() -> SSEResponse:
        return SSEResponse(events(), retry=1500)

    app = Rapidy(http_route_handlers=[stream_events])
    async with AsyncTestClient(app) as client, client.sse_connect('/events') as session:
        event = await session.receive_event()
        assert session.status_code == 200
        assert session.headers['content-type'] == 'text/event-stream; charset=utf-8'
        assert session.retry == 1500
        assert event.event == 'update'
        assert event.id == 'one'
        assert event.json() == {'value': 1}

    await asyncio.wait_for(closed.wait(), timeout=1)


def test_sync_sse_session_iterates_finite_events() -> None:
    async def events() -> AsyncIterator[str]:
        yield 'one'
        yield 'two\nlines'

    @get('/events')
    async def stream_events() -> SSEResponse:
        return SSEResponse(events())

    app = Rapidy(http_route_handlers=[stream_events])
    with TestClient(app) as client, client.sse_connect('/events') as session:
        assert [event.data for event in session] == ['one', 'two\nlines']
