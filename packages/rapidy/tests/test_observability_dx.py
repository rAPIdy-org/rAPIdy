from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from rapidy import Rapidy
from rapidy.__main__ import main
from rapidy.exceptions import HTTPException, HTTPNotFound
from rapidy.http import get, PathParam, post, Request, Response, WebSocket, websocket
from rapidy.middlewares.request_id import RequestIDMiddleware
from rapidy.observability import AccessLogMiddleware, AccessLogRecord, instrument_app, JSONAccessFormatter
from rapidy.openapi import OpenAPIConfig
from rapidy.problems import ProblemDetails, ProblemDetailsRenderer
from rapidy.responses.streaming import StreamResponse
from rapidy.routing import (
    DuplicateRouteNameError,
    InvalidPathParameterError,
    MissingPathParameterError,
    UnexpectedPathParameterError,
    URLPath,
)
from rapidy.serve import MissingUvicornDependencyError
from rapidy.staticfiles import StaticFiles
from rapidy.testing import AsyncTestClient


class DomainError(Exception):
    pass


@pytest.mark.asyncio
async def test_named_reverse_urls_mounts_regex_and_request_root_path(tmp_path: Path) -> None:
    @get('/users/{user_id:\\d+}', name='user.detail')
    async def detail(request: Request, user_id: int = PathParam()) -> dict[str, str | int]:
        return {'user_id': user_id, 'self': request.url_for('user.detail', user_id=user_id)}

    assets = tmp_path / 'assets'
    assets.mkdir()
    (assets / 'app.js').write_text('ok')
    child = Rapidy(http_route_handlers=[detail, StaticFiles('/assets', directory=assets, name='assets')])
    app = Rapidy()
    app.add_subapp('/v1', child)

    assert app.url_for('user.detail', user_id=42) == '/v1/users/42'
    assert app.static_url('assets', 'js/app.js') == '/v1/assets/js/app.js'
    assert app.url_for('assets:index') == '/v1/assets'
    assert URLPath('/items').include_query_params(page=2, tag=['a', 'b']) == '/items?page=2&tag=a&tag=b'
    assert app.route_template('/v1/users/42') == '/v1/users/{user_id:\\d+}'
    assert app.route_template('/v1/users/private') is None

    async with AsyncTestClient(app, root_path='/api') as client:
        response = await client.get('/v1/users/42')
    assert response.json()['self'] == '/api/v1/users/42'

    with pytest.raises(MissingPathParameterError):
        app.url_for('user.detail')
    with pytest.raises(UnexpectedPathParameterError):
        app.url_for('user.detail', user_id=42, extra=True)
    with pytest.raises(InvalidPathParameterError):
        app.url_for('user.detail', user_id='nope')
    with pytest.raises(ValueError, match='non-empty string'):
        StaticFiles('/invalid', directory=assets, name='')


def test_duplicate_route_names_are_typed() -> None:
    @get('/first', name='duplicate')
    async def first() -> str:
        return 'first'

    @get('/second', name='duplicate')
    async def second() -> str:
        return 'second'

    app = Rapidy(http_route_handlers=[first, second])
    with pytest.raises(DuplicateRouteNameError):
        app.url_for('duplicate')


@pytest.mark.asyncio
async def test_access_log_is_low_cardinality_sized_and_redacted() -> None:
    records: list[AccessLogRecord] = []

    @post('/users/{user_id}', name='user.update')
    async def update(request: Request) -> dict[str, int]:
        return {'size': len(await request.read())}

    app = Rapidy(http_route_handlers=[update], middlewares=[RequestIDMiddleware(generator=lambda: 'generated')])
    wrapped = AccessLogMiddleware(app, emit=records.append)
    transport = httpx.ASGITransport(app=wrapped)
    trace_id = '0123456789abcdef0123456789abcdef'
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.post(
            '/users/private-value?token=secret-query',
            content=b'payload',
            headers={
                'Authorization': 'Bearer secret-header',
                'Traceparent': f'00-{trace_id}-0123456789abcdef-01',
                'X-Request-ID': 'incoming-id',
            },
        )
        missing = await client.get('/another-private-value?password=hidden')

    assert response.status_code == 200
    assert missing.status_code == 404
    assert records[0].route == '/users/{user_id}'
    assert records[0].request_size == len(b'payload')
    assert records[0].response_size == len(response.content)
    assert records[0].request_id == 'incoming-id'
    assert records[0].trace_id == trace_id
    assert records[1].route == '{unmatched}'
    serialized = json.dumps([record.as_dict() for record in records])
    assert 'private-value' not in serialized
    assert 'secret-query' not in serialized
    assert 'secret-header' not in serialized
    assert 'hidden' not in serialized


def test_json_access_formatter() -> None:
    formatter = JSONAccessFormatter()
    log_record = logging.LogRecord('rapidy.access', logging.INFO, '', 0, 'request.complete', (), None)
    log_record.rapidy_access = AccessLogRecord('http', 'GET', '/health', 200, 1.5, 0, 2).as_dict()
    assert json.loads(formatter.format(log_record))['route'] == '/health'


@pytest.mark.asyncio
async def test_problem_details_registry_mount_inheritance_and_specificity() -> None:
    renderer = ProblemDetailsRenderer(type_base_url='https://errors.example.test')

    @get('/domain')
    async def domain() -> None:
        private_detail = 'private internal detail'
        raise DomainError(private_detail)

    @get('/missing')
    async def missing() -> None:
        raise HTTPNotFound(text='User was not found')

    child = Rapidy(
        http_route_handlers=[domain, missing],
        exception_handlers={Exception: renderer, HTTPException: renderer},
    )
    root = Rapidy(exception_handlers={Exception: lambda _request, _exc: Response('root', status=500)})
    root.add_subapp('/v1', child)

    async with AsyncTestClient(root) as client:
        domain_response = await client.get('/v1/domain')
        missing_response = await client.get('/v1/missing')

    assert domain_response.status_code == 500
    assert domain_response.headers['content-type'].startswith('application/problem+json')
    assert domain_response.json() == {
        'type': 'https://errors.example.test/500',
        'title': 'Internal Server Error',
        'status': 500,
        'instance': '/v1/domain',
    }
    assert missing_response.status_code == 404
    assert missing_response.json()['detail'] == 'User was not found'
    assert missing_response.json()['title'] == 'Not Found'


def test_problem_details_validation() -> None:
    problem = ProblemDetails(title='Conflict', status=409, extensions={'code': 'duplicate'})
    assert problem.as_dict()['code'] == 'duplicate'
    with pytest.raises(ValueError, match='reserved'):
        ProblemDetails(title='Conflict', status=409, extensions={'status': 'bad'})


@pytest.mark.asyncio
async def test_handler_is_not_called_after_stream_response_started() -> None:
    called = False

    async def body() -> AsyncIterator[bytes]:
        yield b'first'
        raise DomainError

    @get('/stream')
    async def stream() -> StreamResponse:
        return StreamResponse(body())

    def handle(_request: Request, _exception: Exception) -> Response:
        nonlocal called
        called = True
        return Response('handled', status=500)

    app = Rapidy(http_route_handlers=[stream], exception_handlers={DomainError: handle})
    async with AsyncTestClient(app, raise_server_exceptions=False) as client:
        response = await client.get('/stream')
    assert response.status_code == 200
    assert not called


@pytest.mark.asyncio
async def test_official_otel_instrumentation_uses_http_and_websocket_templates() -> None:
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])

    @get('/users/{user_id}', name='user')
    async def user() -> str:
        return 'ok'

    @websocket('/socket/{room}', name='socket')
    async def socket(connection: WebSocket) -> None:
        await connection.accept()
        await connection.send_text('hello')

    app = Rapidy(http_route_handlers=[user, socket])
    records: list[AccessLogRecord] = []
    wrapped = AccessLogMiddleware(
        instrument_app(app, tracer_provider=tracer_provider, meter_provider=meter_provider),
        emit=records.append,
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=wrapped), base_url='http://test') as client:
        response = await client.get('/users/private-user?token=secret')
    assert response.status_code == 200

    incoming = iter([{'type': 'websocket.connect'}])
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return next(incoming)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async with app.lifespan.ctx_manager():
        await wrapped(
            {
                'type': 'websocket',
                'asgi': {'version': '3.0'},
                'http_version': '1.1',
                'scheme': 'ws',
                'path': '/socket/private-room',
                'raw_path': b'/socket/private-room',
                'root_path': '',
                'query_string': b'',
                'headers': [],
                'client': ('127.0.0.1', 1),
                'server': ('127.0.0.1', 2),
                'subprotocols': [],
                'state': {},
            },
            receive,
            send,
        )

    server_spans = [span for span in span_exporter.get_finished_spans() if span.kind.name == 'SERVER']
    assert {span.name for span in server_spans} >= {'GET /users/{user_id}', 'WS /socket/{room}'}
    assert {span.attributes.get('http.route') for span in server_spans} >= {'/users/{user_id}', '/socket/{room}'}
    assert 'private-user' not in repr(server_spans)
    assert 'private-room' not in repr(server_spans)
    metrics = metric_reader.get_metrics_data().resource_metrics
    assert metrics
    assert records[0].route == '/users/{user_id}'
    assert records[1].route == '/socket/{room}'
    assert records[1].status == 101
    assert records[1].response_size == len(b'hello')
    assert records[1].close_code == 1000


@pytest.mark.asyncio
async def test_openapi_docs_preset_is_opt_in_and_uses_conventional_paths() -> None:
    app = Rapidy(openapi_config=OpenAPIConfig.docs(title='Docs', version='1'))
    async with AsyncTestClient(app) as client:
        assert (await client.get('/openapi.json')).status_code == 200
        assert (await client.get('/docs')).status_code == 200
        assert (await client.get('/redoc')).status_code == 200
        assert (await client.get('/schema')).status_code == 404


def test_cli_routes_check_dev_and_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr('rapidy.__main__.run_app', lambda target, **kwargs: calls.append((target, kwargs)))

    main(['dev', 'tests.apps.observability_dx:app', '--reload', '--port', '9001'])
    assert calls == [
        (
            'tests.apps.observability_dx:app',
            {
                'host': '127.0.0.1',
                'port': 9001,
                'workers': 1,
                'timeout_graceful_shutdown': None,
                'reload': True,
            },
        )
    ]
    main(['routes', 'tests.apps.observability_dx:app'])
    assert '/users/{user_id:\\d+}' in capsys.readouterr().out
    main(['check', 'tests.apps.observability_dx:app'])
    assert 'openapi=/openapi.json, /docs, /redoc' in capsys.readouterr().out

    package_root = Path(__file__).parent.parent
    environment = {**os.environ, 'PYTHONPATH': str(package_root)}
    result = subprocess.run(
        [sys.executable, '-m', 'rapidy', 'routes', 'tests.apps.observability_dx:app', '--json'],
        cwd=package_root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    routes = json.loads(result.stdout)
    assert any(route['name'] == 'user' for route in routes)

    def missing_uvicorn(_target: str, **_kwargs: Any) -> None:
        raise MissingUvicornDependencyError

    monkeypatch.setattr('rapidy.__main__.run_app', missing_uvicorn)
    with pytest.raises(SystemExit, match=r"install 'rapidy\[uvicorn\]'"):
        main(['run', 'tests.apps.observability_dx:app'])
