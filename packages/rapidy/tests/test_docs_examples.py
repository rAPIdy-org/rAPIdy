from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import urlopen

import websockets

import httpx
import pytest
from examples import (
    background_files,
    di,
    middleware_mounts,
    openapi,
    parameters,
    production_middlewares,
    quickstart,
    realtime,
    security,
    testing,
)

from tests.live_server import live_server


async def request(app: object, method: str, path: str, **kwargs: object) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),  # type: ignore[arg-type]
        base_url='http://testserver',
    ) as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
async def test_quickstart_and_validation_examples() -> None:
    async with quickstart.app.lifespan.ctx_manager():
        hello = await request(quickstart.app, 'GET', '/')
        created = await request(quickstart.app, 'POST', '/users', json={'name': 'Ada', 'age': 37})
        invalid = await request(quickstart.app, 'POST', '/users', json={'name': 'Ada', 'age': 'unknown'})

    assert hello.json() == {'message': 'Hello, rAPIdy 2.0!'}
    assert created.status_code == 201
    assert created.json() == {'id': 1, 'name': 'Ada', 'age': 37}
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_parameters_example() -> None:
    async with parameters.app.lifespan.ctx_manager():
        response = await request(
            parameters.app,
            'POST',
            '/users/7?page=3',
            json={'display_name': 'Ada'},
            headers={'X-Token': 'secret'},
            cookies={'session': 'session-id'},
        )

    assert response.json() == {
        'user_id': 7,
        'display_name': 'Ada',
        'token': 'secret',
        'page': 3,
        'session': 'session-id',
    }


@pytest.mark.asyncio
async def test_openapi_example() -> None:
    async with openapi.app.lifespan.ctx_manager():
        schema = await request(openapi.app, 'GET', '/schema/openapi.json')
        created = await request(openapi.app, 'POST', '/items?notify=true', json={'name': 'Example'})

    assert schema.status_code == 200
    assert schema.json()['info']['title'] == 'Items API'
    assert schema.json()['paths']['/items']['post']['operationId'] == 'createItem'
    assert created.status_code == 201
    assert created.json() == {'id': 1, 'name': 'Example'}


@pytest.mark.asyncio
async def test_security_example(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ITEMS_API_KEY', 'example-key')
    async with security.app.lifespan.ctx_manager():
        denied = await request(security.app, 'GET', '/items')
        allowed = await request(security.app, 'GET', '/items', headers={'X-API-Key': 'example-key'})
        health = await request(security.app, 'GET', '/health')

    assert denied.status_code == 401
    assert allowed.json()['identity_matches_request'] is True
    assert allowed.json()['scopes'] == ['items:read']
    assert health.text == 'ok'


@pytest.mark.asyncio
async def test_di_middleware_mount_and_streaming_examples() -> None:
    async with di.app.lifespan.ctx_manager():
        context_response = await request(di.app, 'GET', '/context')
    assert context_response.json()['service'] == 'users'
    assert context_response.json()['request_id']

    async with middleware_mounts.app.lifespan.ctx_manager():
        mounted = await request(middleware_mounts.app, 'GET', '/api/items/42', headers={'X-Token': 'secret'})
    assert mounted.json() == {'item': '42', 'token': 'secret'}
    assert mounted.headers['X-Authenticated'] == 'true'

    async with realtime.app.lifespan.ctx_manager():
        streamed = await request(realtime.app, 'GET', '/download')
        events = await request(realtime.app, 'GET', '/events')
    assert streamed.text == 'first\nsecond\n'
    assert events.headers['content-type'] == 'text/event-stream; charset=utf-8'
    assert 'id: 0\nevent: tick\ndata: {"index": 0}' in events.text


@pytest.mark.asyncio
async def test_production_middlewares_example() -> None:
    forwarded_https = {'X-Forwarded-Proto': 'https'}
    async with production_middlewares.app.lifespan.ctx_manager():
        response = await request(
            production_middlewares.app,
            'GET',
            '/report',
            headers={
                **forwarded_https,
                'Origin': 'https://console.example.com',
                'Accept-Encoding': 'gzip',
            },
        )
        preflight = await request(
            production_middlewares.app,
            'OPTIONS',
            '/report',
            headers={
                **forwarded_https,
                'Origin': 'https://console.example.com',
                'Access-Control-Request-Method': 'GET',
            },
        )

    assert response.status_code == 200
    assert response.json()['request_id'] == response.headers['X-Request-ID']
    assert response.headers['Content-Encoding'] == 'gzip'
    assert response.headers['Access-Control-Allow-Origin'] == 'https://console.example.com'
    assert preflight.status_code == 204


@pytest.mark.asyncio
async def test_background_files_example() -> None:
    background_files.notifications.clear()
    async with background_files.app.lifespan.ctx_manager():
        accepted = await request(background_files.app, 'POST', '/exports')
        ranged = await request(
            background_files.app,
            'GET',
            '/downloads/report',
            headers={'Range': 'bytes=0-5'},
        )
        index = await request(background_files.app, 'GET', '/assets/')

    assert accepted.status_code == 202
    assert background_files.notifications == ['export:20']
    assert ranged.status_code == 206
    assert ranged.text == 'rAPIdy'
    assert 'Static files are ready' in index.text


@pytest.mark.parametrize('runtime', ['granian', 'uvicorn'])
def test_quickstart_live(runtime: str) -> None:
    with live_server(runtime, 'examples.quickstart:app') as base_url:
        with urlopen(f'{base_url}/', timeout=5) as response:  # noqa: S310
            assert response.status == 200
            assert json.load(response) == {'message': 'Hello, rAPIdy 2.0!'}
        with pytest.raises(HTTPError) as error, urlopen(f'{base_url}/missing', timeout=5):  # noqa: S310
            pass
        assert error.value.code == 404


def test_testing_example() -> None:
    testing.test_health()


@pytest.mark.asyncio
@pytest.mark.parametrize('runtime', ['granian', 'uvicorn'])
async def test_realtime_websocket_live(runtime: str) -> None:
    with live_server(runtime, 'examples.realtime:app') as base_url:
        uri = base_url.replace('http://', 'ws://') + '/ws'
        async with websockets.connect(uri) as client:
            await client.send('hello')
            assert await client.recv() == 'hello'
            await client.send(b'bytes')
            assert await client.recv() == b'bytes'
