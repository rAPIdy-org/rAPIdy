from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import pytest
from httpx import ASGITransport, AsyncClient

import rapidy
from rapidy import Rapidy
from rapidy.http import get, Request, Response
from rapidy.serve import MissingUvicornDependencyError, run_app
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


@pytest.mark.parametrize('runtime', ['granian', 'hypercorn', 'uvicorn', 'rapidy'])
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


def test_deprecated_application_arguments_are_accepted_as_no_ops() -> None:
    with pytest.warns(DeprecationWarning, match='deprecated and ignored') as warnings_info:
        app = Rapidy(logger=object(), handler_args={'expect_handler': object()})

    assert isinstance(app, Rapidy)
    assert len(warnings_info) == 2
    assert all('deprecated and ignored' in str(item.message) for item in warnings_info)


def test_run_app_uses_programmatic_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, dict[str, Any]]] = []

    def fake_run(app: Any, **kwargs: Any) -> None:
        calls.append((app, kwargs))

    monkeypatch.setattr('uvicorn.run', fake_run)
    run_app(
        'tests.apps.ping_app:app',
        host='127.0.0.1',
        port=9000,
        workers=2,
        timeout_graceful_shutdown=7,
    )

    assert calls == [
        (
            'tests.apps.ping_app:app',
            {
                'host': '127.0.0.1',
                'app_dir': str(Path.cwd()),
                'port': 9000,
                'proxy_headers': False,
                'workers': 2,
                'timeout_graceful_shutdown': 7,
            },
        )
    ]

    calls.clear()
    run_app('tests.apps.ping_app:app', proxy_headers=True)
    assert calls[0][1]['proxy_headers'] is True

    app = Rapidy(http_route_handlers=[ping])
    with pytest.raises(ValueError, match='import string'):
        run_app(app, workers=2)


def test_run_app_explains_missing_uvicorn_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def missing_uvicorn(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == 'uvicorn':
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', missing_uvicorn)
    with pytest.raises(MissingUvicornDependencyError, match=r'rapidy\[uvicorn\]'):
        run_app('tests.apps.ping_app:app')
