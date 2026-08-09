from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import (
    Request as URLRequest,
    urlopen,
)

import pytest

from rapidy import Rapidy
from rapidy.background import BackgroundTask, BackgroundTasks
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.http import get, HTTPRouter, Response
from rapidy.middlewares import get_request_id, RequestIDMiddleware
from rapidy.responses import FileResponse, StreamResponse
from rapidy.security import SecurityConfig
from rapidy.staticfiles import StaticFiles
from rapidy.testing import AsyncTestClient
from tests.live_server import live_server


class RequestResource:
    pass


class RequestResourceProvider(Provider):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    @provide(scope=Scope.REQUEST)
    async def resource(self) -> AsyncIterator[RequestResource]:
        self.events.append('di_entered')
        try:
            yield RequestResource()
        finally:
            self.events.append('di_finalized')


@pytest.mark.asyncio
async def test_background_tasks_run_after_body_before_di_finalizer_and_keep_context() -> None:
    events: list[str] = []

    def sync_task(label: str) -> None:
        events.append(f'{label}:{get_request_id()}')

    async def async_task() -> None:
        events.append(f'async:{get_request_id()}')

    @get('/')
    async def handler(resource: FromDI[RequestResource]) -> Response:
        assert isinstance(resource, RequestResource)
        tasks = BackgroundTasks()
        tasks.add_task(sync_task, 'sync')
        tasks.add_task(async_task)
        return Response('ok', background=tasks)

    app = Rapidy(
        http_route_handlers=[handler],
        middlewares=[RequestIDMiddleware(generator=lambda: 'request-20')],
        di_providers=[RequestResourceProvider(events)],
    )
    async with AsyncTestClient(app) as client:
        response = await client.get('/')

    assert response.status_code == 200
    assert response.text == 'ok'
    assert events == [
        'di_entered',
        'sync:request-20',
        'async:request-20',
        'di_finalized',
    ]


@pytest.mark.asyncio
async def test_stream_background_starts_only_after_final_body_frame() -> None:
    events: list[str] = []

    async def chunks() -> AsyncIterator[bytes]:
        events.append('chunk')
        yield b'data'
        events.append('stream_finished')

    async def after() -> None:
        events.append('background')

    @get('/')
    async def handler() -> StreamResponse:
        return StreamResponse(chunks(), background=BackgroundTask(after))

    app = Rapidy(http_route_handlers=[handler])
    async with AsyncTestClient(app) as client:
        response = await client.get('/')

    assert response.content == b'data'
    assert events == ['chunk', 'stream_finished', 'background']


@pytest.mark.asyncio
async def test_stream_disconnect_skips_background_task() -> None:
    events: list[str] = []
    body_started = asyncio.Event()

    async def chunks() -> AsyncIterator[bytes]:
        body_started.set()
        await asyncio.Event().wait()
        yield b'unreachable'

    async def after() -> None:
        events.append('background')

    @get('/')
    async def handler() -> StreamResponse:
        return StreamResponse(chunks(), background=BackgroundTask(after))

    receive = _DisconnectReceive(body_started)
    await Rapidy(http_route_handlers=[handler])(_scope('/'), receive, _discard_send)

    assert events == []


@pytest.mark.asyncio
async def test_background_failure_is_logged_and_stops_later_tasks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    events: list[str] = []

    async def broken() -> None:
        events.append('broken')
        msg = 'background exploded'
        raise RuntimeError(msg)

    async def skipped() -> None:
        events.append('skipped')

    @get('/')
    async def handler() -> Response:
        tasks = BackgroundTasks([BackgroundTask(broken), BackgroundTask(skipped)])
        return Response('already sent', background=tasks)

    caplog.set_level(logging.ERROR)
    async with AsyncTestClient(Rapidy(http_route_handlers=[handler]), raise_server_exceptions=False) as client:
        response = await client.get('/')

    assert response.status_code == 200
    assert response.text == 'already sent'
    assert events == ['broken']
    assert 'Unhandled exception in response background task' in caplog.text


@pytest.mark.asyncio
async def test_background_cancellation_propagates_then_finalizes_request_di() -> None:
    events: list[str] = []
    entered = asyncio.Event()

    async def background() -> None:
        events.append('background_entered')
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            events.append('background_cancelled')

    @get('/')
    async def handler(resource: FromDI[RequestResource]) -> Response:
        assert isinstance(resource, RequestResource)
        return Response('sent', background=BackgroundTask(background))

    app = Rapidy(http_route_handlers=[handler], di_providers=[RequestResourceProvider(events)])
    sent: list[dict[str, Any]] = []
    receive = _Receive()

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async with app.lifespan.ctx_manager():
        request_task = asyncio.create_task(app(_scope('/'), receive, send))
        await entered.wait()
        assert not request_task.done()
        request_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request_task

    assert sent[-1]['type'] == 'http.response.body'
    assert sent[-1]['more_body'] is False
    assert events == ['di_entered', 'background_entered', 'background_cancelled', 'di_finalized']


@pytest.mark.asyncio
async def test_file_response_get_head_range_and_conditionals(tmp_path: Path) -> None:
    file_path = tmp_path / 'hello.txt'
    file_path.write_bytes(b'0123456789')

    @get('/file')
    async def file_handler() -> FileResponse:
        return FileResponse(file_path, filename='привет.txt')

    app = Rapidy(http_route_handlers=[file_handler])
    async with AsyncTestClient(app) as client:
        response = await client.get('/file')
        head_response = await client.head('/file')
        partial = await client.get('/file', headers={'Range': 'bytes=2-5'})
        full_range = await client.get('/file', headers={'Range': 'bytes=0-9'})
        head_range = await client.head('/file', headers={'Range': 'bytes=2-5'})
        suffix = await client.get('/file', headers={'Range': 'bytes=-3'})
        unsatisfied = await client.get('/file', headers={'Range': 'bytes=20-30'})
        multipart = await client.get('/file', headers={'Range': 'bytes=0-1,4-5'})
        malformed_ranges = [
            await client.get('/file', headers={'Range': value})
            for value in ('bytes=+1-2', 'bytes=1_0-', 'bytes= 1-2', 'bytes=1 -2', 'bytes=1- 2', 'bytes =1-2')
        ]
        not_modified = await client.get('/file', headers={'If-None-Match': response.headers['etag']})
        date_not_modified = await client.get(
            '/file', headers={'If-Modified-Since': response.headers['last-modified']}
        )
        range_miss = await client.get(
            '/file',
            headers={'Range': 'bytes=0-1', 'If-Range': '"different"'},
        )

    assert response.content == b'0123456789'
    assert response.headers['content-length'] == '10'
    assert response.headers['accept-ranges'] == 'bytes'
    assert response.headers['content-type'].startswith('text/plain')
    assert "filename*=UTF-8''" in response.headers['content-disposition']
    assert head_response.content == b''
    assert head_response.headers['content-length'] == '10'
    assert partial.status_code == 206
    assert partial.content == b'2345'
    assert partial.headers['content-range'] == 'bytes 2-5/10'
    assert full_range.status_code == 206
    assert full_range.headers['content-range'] == 'bytes 0-9/10'
    assert head_range.status_code == 206
    assert head_range.content == b''
    assert head_range.headers['content-length'] == '4'
    assert suffix.content == b'789'
    assert unsatisfied.status_code == 416
    assert unsatisfied.headers['content-range'] == 'bytes */10'
    assert multipart.status_code == 200
    assert multipart.content == b'0123456789'
    assert 'content-range' not in multipart.headers
    assert all(response.status_code == 416 for response in malformed_ranges)
    assert not_modified.status_code == 304
    assert not_modified.content == b''
    assert date_not_modified.status_code == 304
    assert range_miss.status_code == 200
    assert range_miss.content == b'0123456789'


@pytest.mark.asyncio
@pytest.mark.parametrize('extension', ['http.response.pathsend', 'http.response.zerocopysend'])
async def test_file_response_uses_asgi_send_extension(tmp_path: Path, extension: str) -> None:
    file_path = tmp_path / 'payload.bin'
    file_path.write_bytes(b'extension-body')

    @get('/')
    async def handler() -> FileResponse:
        return FileResponse(file_path)

    messages: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        if message.get('type') == 'http.response.zerocopysend':
            file_object = message['file']
            file_object.seek(message['offset'])
            message = {**message, 'observed': file_object.read(message['count'])}
        messages.append(message)

    await Rapidy(http_route_handlers=[handler])(
        _scope('/', extensions={extension: {}}),
        _Receive(),
        send,
    )

    assert [message['type'] for message in messages] == ['http.response.start', extension]
    if extension == 'http.response.pathsend':
        assert messages[-1]['path'] == str(file_path.absolute())
    else:
        assert messages[-1]['observed'] == b'extension-body'
        assert messages[-1]['more_body'] is False


@pytest.mark.asyncio
async def test_range_uses_zerocopy_instead_of_pathsend(tmp_path: Path) -> None:
    file_path = tmp_path / 'payload.bin'
    file_path.write_bytes(b'extension-body')

    @get('/')
    async def handler() -> FileResponse:
        return FileResponse(file_path)

    messages: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        if message.get('type') == 'http.response.zerocopysend':
            file_object = message['file']
            file_object.seek(message['offset'])
            message = {**message, 'observed': file_object.read(message['count'])}
        messages.append(message)

    await Rapidy(http_route_handlers=[handler])(
        _scope(
            '/',
            extensions={'http.response.pathsend': {}, 'http.response.zerocopysend': {}},
            headers=[(b'range', b'bytes=2-5')],
        ),
        _Receive(),
        send,
    )

    assert messages[0]['status'] == 206
    assert messages[-1]['type'] == 'http.response.zerocopysend'
    assert messages[-1]['observed'] == b'tens'


@pytest.mark.asyncio
async def test_missing_file_keeps_response_middleware_headers(tmp_path: Path) -> None:
    @get('/')
    async def handler() -> FileResponse:
        return FileResponse(tmp_path / 'missing.txt')

    app = Rapidy(
        http_route_handlers=[handler],
        middlewares=[RequestIDMiddleware(generator=lambda: 'missing-file')],
    )
    async with AsyncTestClient(app) as client:
        response = await client.get('/')

    assert response.status_code == 404
    assert response.headers['x-request-id'] == 'missing-file'


@pytest.mark.asyncio
async def test_static_files_index_cache_mount_and_security(tmp_path: Path) -> None:
    static_root = tmp_path / 'static'
    static_root.mkdir()
    (static_root / 'index.html').write_text('<h1>index</h1>')
    (static_root / 'app.js').write_text('console.log(20)')
    nested = static_root / 'nested'
    nested.mkdir()
    (nested / 'value.txt').write_text('nested')
    (static_root / '.env').write_text('API_KEY=hunter2')
    (nested / '.secret').write_text('nested-secret')
    secret = tmp_path / 'secret.txt'
    secret.write_text('secret')
    (static_root / 'escape.txt').symlink_to(secret)
    (static_root / 'inside.txt').symlink_to(static_root / 'app.js')

    router = HTTPRouter('/v1', [StaticFiles('/assets', directory=static_root, html=True)])
    app = Rapidy(http_route_handlers=[router])
    async with AsyncTestClient(app, follow_redirects=False) as client:
        redirect = await client.get('/v1/assets?version=20')
        index = await client.get('/v1/assets/')
        asset = await client.get('/v1/assets/app.js')
        nested_asset = await client.get('/v1/assets/nested/value.txt')
        dotfile = await client.get('/v1/assets/.env')
        nested_dotfile = await client.get('/v1/assets/nested/.secret')
        symlink = await client.get('/v1/assets/escape.txt')

    assert redirect.status_code == 307
    assert redirect.headers['location'] == '/v1/assets/?version=20'
    assert index.text == '<h1>index</h1>'
    assert asset.text == 'console.log(20)'
    assert asset.headers['cache-control'] == 'public, max-age=3600'
    assert nested_asset.text == 'nested'
    assert dotfile.status_code == 404
    assert nested_dotfile.status_code == 404
    assert symlink.status_code == 404
    static_routes = [route for route in app.routes if '/assets' in route.path]
    assert static_routes
    assert all(route.route_kwargs['include_in_schema'] is False for route in static_routes)

    traversal_messages: list[dict[str, Any]] = []

    async def traversal_send(message: dict[str, Any]) -> None:
        traversal_messages.append(message)

    await app(
        _scope('/v1/assets/../secret.txt', raw_path=b'/v1/assets/../secret.txt'),
        _Receive(),
        traversal_send,
    )
    assert traversal_messages[0]['status'] == 404

    follow_app = Rapidy(
        http_route_handlers=[
            StaticFiles('/assets', directory=static_root, follow_symlinks=True),
        ]
    )
    async with AsyncTestClient(follow_app) as client:
        internal_link = await client.get('/assets/inside.txt')
        external_link = await client.get('/assets/escape.txt')
    assert internal_link.text == 'console.log(20)'
    assert external_link.status_code == 404



@pytest.mark.asyncio
async def test_static_files_inherit_security_and_require_explicit_public_dotfile_opt_in(tmp_path: Path) -> None:
    static_root = tmp_path / 'static'
    static_root.mkdir()
    (static_root / 'app.js').write_text('console.log(20)')
    (static_root / '.env').write_text('API_KEY=hunter2')
    app = Rapidy(
        security=SecurityConfig(guards=[lambda _request: False]),
        http_route_handlers=[
            StaticFiles('/protected', directory=static_root),
            StaticFiles('/public', directory=static_root, public=True),
            StaticFiles('/dotfiles', directory=static_root, allow_dotfiles=True, public=True),
        ],
    )
    async with AsyncTestClient(app) as client:
        inherited_security = await client.get('/protected/app.js')
        explicitly_public = await client.get('/public/app.js')
        explicitly_allowed_dotfile = await client.get('/dotfiles/.env')

    assert inherited_security.status_code == 403
    assert explicitly_public.text == 'console.log(20)'
    assert explicitly_allowed_dotfile.text == 'API_KEY=hunter2'


@pytest.mark.asyncio
async def test_static_file_symlink_swap_cannot_escape_validated_root(tmp_path: Path) -> None:
    static_root = tmp_path / 'static'
    static_root.mkdir()
    asset = static_root / 'asset.txt'
    asset.write_text('public')
    secret = tmp_path / 'secret.txt'
    secret.write_text('secret')

    async def swap_after_resolution(request, call_next) -> Any:
        response = await call_next(request)
        asset.unlink()
        asset.symlink_to(secret)
        return response

    app = Rapidy(
        http_route_handlers=[StaticFiles('/assets', directory=static_root)],
        middlewares=[swap_after_resolution],
    )
    async with AsyncTestClient(app) as client:
        response = await client.get('/assets/asset.txt')

    assert response.status_code == 404
    assert response.content != b'secret'


@pytest.mark.asyncio
async def test_allowed_internal_symlink_is_pinned_before_a_later_swap(tmp_path: Path) -> None:
    static_root = tmp_path / 'static'
    static_root.mkdir()
    public = static_root / 'public.txt'
    public.write_text('public')
    alias = static_root / 'alias.txt'
    alias.symlink_to(public)
    secret = tmp_path / 'secret.txt'
    secret.write_text('secret')

    async def swap_after_resolution(request, call_next) -> Any:
        response = await call_next(request)
        alias.unlink()
        alias.symlink_to(secret)
        return response

    app = Rapidy(
        http_route_handlers=[
            StaticFiles('/assets', directory=static_root, follow_symlinks=True),
        ],
        middlewares=[swap_after_resolution],
    )
    async with AsyncTestClient(app) as client:
        response = await client.get('/assets/alias.txt')

    assert response.status_code == 200
    assert response.text == 'public'


def test_file_and_static_configuration_rejects_unsafe_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='control characters'):
        FileResponse(tmp_path / 'file', filename='bad\r\nname')
    with pytest.raises(ValueError, match='literal URL prefix'):
        StaticFiles('/../assets', directory=tmp_path)
    with pytest.raises(ValueError, match='control characters'):
        StaticFiles('/assets', directory=tmp_path, cache_control='public\r\nX-Bad: yes')
    with pytest.raises(ValueError, match='dotfile index'):
        StaticFiles('/assets', directory=tmp_path, index_file='.index.html')


@pytest.mark.parametrize('runtime', ['granian', 'uvicorn'])
def test_file_and_static_live_runtimes(runtime: str) -> None:
    with live_server(runtime, 'tests.apps.background_files_app:app') as base_url:
        range_request = URLRequest(f'{base_url}/download', headers={'Range': 'bytes=2-5'})  # noqa: S310
        with urlopen(range_request, timeout=5) as response:  # noqa: S310
            assert response.status == 206
            assert response.headers['Content-Range'] == 'bytes 2-5/11'
            assert response.read() == b'2345'
        with urlopen(f'{base_url}/static/', timeout=5) as response:  # noqa: S310
            assert response.status == 200
            assert b'rAPIdy static' in response.read()
        with pytest.raises(HTTPError) as traversal_error, urlopen(  # noqa: S310
            f'{base_url}/static/%2e%2e/background_files_app.py', timeout=5
        ):
            pass
        assert traversal_error.value.code == 404


class _Receive:
    def __init__(self) -> None:
        self._sent_request = False
        self._wait = asyncio.Event()

    async def __call__(self) -> dict[str, Any]:
        if not self._sent_request:
            self._sent_request = True
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        await self._wait.wait()
        return {'type': 'http.disconnect'}


class _DisconnectReceive:
    def __init__(self, body_started: asyncio.Event) -> None:
        self._body_started = body_started
        self._sent_request = False

    async def __call__(self) -> dict[str, Any]:
        if not self._sent_request:
            self._sent_request = True
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        await self._body_started.wait()
        return {'type': 'http.disconnect'}


async def _discard_send(_message: dict[str, Any]) -> None:
    return None


def _scope(
    path: str,
    *,
    raw_path: bytes | None = None,
    extensions: dict[str, dict[str, Any]] | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    return {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'http',
        'path': path,
        'raw_path': raw_path if raw_path is not None else path.encode(),
        'query_string': b'',
        'headers': headers or [],
        'client': ('127.0.0.1', 1234),
        'server': ('testserver', 80),
        'root_path': '',
        'state': {},
        'extensions': extensions or {},
    }
