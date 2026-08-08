from __future__ import annotations

from typing import Any
from urllib.request import urlopen

import pytest
from httpx import ASGITransport, AsyncClient

import rapidy
from rapidy import Rapidy
from rapidy.http import get, Request, Response
from rapidy.serve import run_app
from rapidy.version import SERVER_INFO
from tests.live_server import live_server


@get('/ping')
async def ping() -> str:
    return 'pong'


@get('/request')
async def request_view(request: Request) -> Response:
    assert request.method == 'GET'
    assert request.path == '/request'
    assert request.headers['x-test'] == 'yes'
    assert request.path_params == {}
    assert request.app['shared'] == 'value'
    request.state.seen = True
    return Response('request-ok', headers={'x-request-state': str(request.state.seen).lower()})


@pytest.mark.asyncio
async def test_in_process_http_and_public_facade() -> None:
    app = Rapidy(http_route_handlers=[ping, request_view], server_info_in_response=True)
    app['shared'] = 'value'
    assert app.state.shared == 'value'
    assert rapidy.__all__ == ('__version__', 'Rapidy', 'run_app')

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        ping_response = await client.get('/ping')
        request_response = await client.get('/request', headers={'x-test': 'yes'})
        not_found = await client.get('/missing')

    assert ping_response.status_code == 200
    assert ping_response.text == 'pong'
    assert ping_response.headers['content-type'] == 'text/plain; charset=utf-8'
    assert ping_response.headers['server'] == SERVER_INFO
    assert request_response.status_code == 200
    assert request_response.text == 'request-ok'
    assert request_response.headers['x-request-state'] == 'true'
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_websocket_is_closed_with_1011_before_startup() -> None:
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {'type': 'websocket.connect'}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await Rapidy()({'type': 'websocket'}, receive, send)
    assert messages == [
        {
            'type': 'websocket.close',
            'code': 1011,
            'reason': 'Application startup has not completed',
        }
    ]


@pytest.mark.parametrize('runtime', ['granian', 'uvicorn', 'rapidy'])
def test_live_ping(runtime: str) -> None:
    with (
        live_server(runtime, 'tests.apps.ping_app:app') as base_url,
        urlopen(f'{base_url}/ping', timeout=5) as response,  # noqa: S310
    ):
        assert response.status == 200
        assert response.read() == b'pong'


def test_response_serializes_structured_body_types() -> None:
    response = Response({'implemented': True})
    assert response.text == '{"implemented": true}'


def test_run_app_uses_programmatic_granian(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    class FakeServer:
        def __init__(self, **kwargs: Any) -> None:
            calls['init'] = kwargs

        def serve(self, **kwargs: Any) -> None:
            calls['serve'] = kwargs

    monkeypatch.setattr('granian.server.Server', FakeServer)
    app = Rapidy(http_route_handlers=[ping])
    run_app(app, host='127.0.0.1', port=9000, workers=2, workers_kill_timeout=7)

    assert calls['init']['address'] == '127.0.0.1'
    assert calls['init']['port'] == 9000
    assert calls['init']['workers'] == 2
    assert calls['init']['workers_kill_timeout'] == 7
    assert calls['serve']['target_loader']('unused') is app
