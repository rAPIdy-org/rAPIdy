from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from rapidy import (
    http as rapidy_http,
    Rapidy,
)
from rapidy.depends import FromDI, provide, Provider, Scope
from rapidy.endpoint_handlers.http.annotation_checkers import annotation_is_stream_response
from rapidy.http import (
    get,
    middleware,
    post,
    Request,
    Response,
    SSEResponse,
    StreamResponse,
)
from rapidy.responses import SSEEvent
from rapidy.responses.streaming import (
    StreamAlreadyFinishedError,
    StreamNotPreparedError,
)
from rapidy.typedefs import CallNext
from tests.live_server import live_server


class FakeHTTPTransport:
    def __init__(self) -> None:
        self.incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.sent: list[dict[str, Any]] = []
        self.body_sent = asyncio.Event()

    def feed(self, message: dict[str, Any]) -> None:
        self.incoming.put_nowait(message)

    async def receive(self) -> dict[str, Any]:
        return await self.incoming.get()

    async def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)
        if message.get('type') == 'http.response.body' and message.get('more_body'):
            self.body_sent.set()


def decode_headers(message: dict[str, Any]) -> dict[str, str]:
    return {
        bytes(name).decode('latin-1').lower(): bytes(value).decode('latin-1')
        for name, value in message['headers']
    }


def make_request(
    transport: FakeHTTPTransport,
    *,
    http_version: str = '1.1',
    app: Rapidy | None = None,
) -> Request:
    current_app = app or Rapidy()
    scope: dict[str, Any] = {
        'type': 'http',
        'http_version': http_version,
        'method': 'GET',
        'path': '/',
        'query_string': b'',
        'headers': [],
        'state': {},
        'app': current_app,
    }
    request = Request(scope, transport.receive)
    request._asgi_send = transport.send
    request._asgi_receive = transport.receive
    return request


async def run_http(
    app: Rapidy,
    path: str,
    *,
    method: str = 'GET',
    http_version: str = '1.1',
) -> list[dict[str, Any]]:
    transport = FakeHTTPTransport()
    transport.feed({'type': 'http.request', 'body': b'', 'more_body': False})
    scope: dict[str, Any] = {
        'type': 'http',
        'http_version': http_version,
        'method': method,
        'path': path,
        'query_string': b'',
        'headers': [],
        'state': {},
    }
    async with app.lifespan.ctx_manager():
        await app(scope, transport.receive, transport.send)
    return transport.sent


@pytest.mark.asyncio
async def test_iter_stream_frames_and_mutable_contract() -> None:
    async def chunks() -> AsyncIterator[bytes | str]:
        yield b'one'
        yield 'два'

    transport = FakeHTTPTransport()
    response = StreamResponse(
        body=chunks(),
        status=206,
        headers={'x-test': 'yes', 'Content-Length': '100', 'Transfer-Encoding': 'chunked'},
        content_type='text/plain',
        charset='utf-8',
    )
    response.status = 201
    response.headers['x-mutated'] = 'true'
    await response._send_stream(transport.send, transport.receive, server_info='Rapidy/test')

    start = transport.sent[0]
    headers = decode_headers(start)
    assert start['status'] == 201
    assert headers == {
        'x-test': 'yes',
        'x-mutated': 'true',
        'content-type': 'text/plain; charset=utf-8',
        'server': 'Rapidy/test',
    }
    assert transport.sent[1:] == [
        {'type': 'http.response.body', 'body': b'one', 'more_body': True},
        {'type': 'http.response.body', 'body': 'два'.encode(), 'more_body': True},
        {'type': 'http.response.body', 'body': b'', 'more_body': False},
    ]


@pytest.mark.asyncio
async def test_default_empty_stream_and_utf16() -> None:
    empty_transport = FakeHTTPTransport()
    await StreamResponse()._send_stream(empty_transport.send, empty_transport.receive)
    assert decode_headers(empty_transport.sent[0])['content-type'] == 'application/octet-stream'
    assert empty_transport.sent[1] == {'type': 'http.response.body', 'body': b'', 'more_body': False}

    async def chunks() -> AsyncIterator[str]:
        yield 'text'

    encoded_transport = FakeHTTPTransport()
    await StreamResponse(body=chunks(), charset='utf-16')._send_stream(
        encoded_transport.send,
        encoded_transport.receive,
    )
    assert decode_headers(encoded_transport.sent[0])['content-type'].endswith('charset=utf-16')
    assert encoded_transport.sent[1]['body'] == 'text'.encode('utf-16')


@pytest.mark.asyncio
async def test_imperative_prepare_write_eof_and_errors() -> None:
    transport = FakeHTTPTransport()
    response = StreamResponse(headers={'content-length': '9'})
    with pytest.raises(StreamNotPreparedError):
        await response.write(b'early')
    with pytest.raises(StreamNotPreparedError):
        await response.write_eof()

    request = make_request(transport)
    await response.prepare(request)
    await response.prepare(request)
    await response.write(b'a')
    await response.write_eof(b'z')
    await response.write_eof()
    with pytest.raises(StreamAlreadyFinishedError, match='write'):
        await response.write(b'late')
    before = list(transport.sent)
    await response._send_stream(transport.send, transport.receive)

    assert transport.sent == before
    assert sum(message['type'] == 'http.response.start' for message in transport.sent) == 1
    assert transport.sent[-1] == {'type': 'http.response.body', 'body': b'z', 'more_body': False}


@pytest.mark.asyncio
async def test_disconnect_cancels_iteration_and_acloses() -> None:
    finalized = asyncio.Event()
    release = asyncio.Event()

    async def chunks() -> AsyncIterator[bytes]:
        try:
            yield b'first'
            await release.wait()
            yield b'never'
        finally:
            finalized.set()

    transport = FakeHTTPTransport()
    response = StreamResponse(body=chunks())
    task = asyncio.create_task(response._send_stream(transport.send, transport.receive))
    await transport.body_sent.wait()
    transport.feed({'type': 'http.request', 'body': b'unread', 'more_body': True})
    transport.feed({'type': 'http.disconnect'})
    await task

    assert finalized.is_set()
    assert not any(message.get('more_body') is False for message in transport.sent)
    await asyncio.sleep(0)
    task_names = {current.get_coro().__qualname__ for current in asyncio.all_tasks()}
    assert not any(name.endswith(('_listen_for_disconnect', '_iterate_and_send')) for name in task_names)


@pytest.mark.asyncio
async def test_disconnect_calls_custom_aclose_once() -> None:
    class ClosableBody:
        def __init__(self) -> None:
            self.closed = 0
            self.release = asyncio.Event()

        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b'first'
            await self.release.wait()

        async def aclose(self) -> None:
            self.closed += 1

    body = ClosableBody()
    transport = FakeHTTPTransport()
    response = StreamResponse(body=body)
    task = asyncio.create_task(response._send_stream(transport.send, transport.receive))
    await transport.body_sent.wait()
    transport.feed({'type': 'http.disconnect'})
    await task

    assert body.closed == 1


@pytest.mark.asyncio
async def test_http_request_messages_do_not_interrupt_stream() -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b'a'
        await asyncio.sleep(0)
        yield b'b'

    transport = FakeHTTPTransport()
    transport.feed({'type': 'http.request', 'body': b'one', 'more_body': True})
    transport.feed({'type': 'http.request', 'body': b'two', 'more_body': False})
    await StreamResponse(body=chunks())._send_stream(transport.send, transport.receive)
    assert transport.sent[-1] == {'type': 'http.response.body', 'body': b'', 'more_body': False}


@pytest.mark.asyncio
async def test_iteration_exception_is_logged_and_not_replayed(caplog: pytest.LogCaptureFixture) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b'partial'
        msg = 'broken stream'
        raise RuntimeError(msg)

    transport = FakeHTTPTransport()
    with caplog.at_level('ERROR', logger='rapidy'):
        await StreamResponse(body=chunks())._send_stream(transport.send, transport.receive)

    assert transport.sent[-1] == {'type': 'http.response.body', 'body': b'partial', 'more_body': True}
    assert 'Unhandled error while streaming response body' in caplog.text


@pytest.mark.asyncio
async def test_sse_frames_headers_retry_and_user_override() -> None:
    async def events() -> AsyncIterator[SSEEvent | str | dict[str, Any]]:
        yield 'hello'
        yield {'a': 1}
        yield SSEEvent(data='a\nb', event='changed', id='7')

    transport = FakeHTTPTransport()
    response = SSEResponse(events(), headers={'Cache-Control': 'max-age=1'}, retry=5000)
    await response._send_stream(transport.send, transport.receive)

    headers = decode_headers(transport.sent[0])
    assert headers['content-type'] == 'text/event-stream; charset=utf-8'
    assert headers['cache-control'] == 'max-age=1'
    assert headers['connection'] == 'keep-alive'
    assert 'content-length' not in headers
    assert [message['body'] for message in transport.sent[1:]] == [
        b'retry: 5000\n\n',
        b'data: hello\n\n',
        b'data: {"a": 1}\n\n',
        b'id: 7\nevent: changed\ndata: a\ndata: b\n\n',
        b'',
    ]
    assert all(message['more_body'] for message in transport.sent[1:-1])
    assert transport.sent[-1]['more_body'] is False


@pytest.mark.asyncio
async def test_sse_http2_omits_connection_header() -> None:
    async def events() -> AsyncIterator[str]:
        yield 'hello'

    transport = FakeHTTPTransport()
    response = SSEResponse(events())
    await response.prepare(make_request(transport, http_version='2'))
    await response._send_stream(transport.send, transport.receive)

    headers = decode_headers(transport.sent[0])
    assert headers['cache-control'] == 'no-cache'
    assert 'connection' not in headers


def test_stream_checker_signatures_and_exports() -> None:
    assert annotation_is_stream_response(StreamResponse)
    assert annotation_is_stream_response(SSEResponse)
    assert annotation_is_stream_response(Response)
    assert not annotation_is_stream_response(dict)
    assert rapidy_http.StreamResponse is StreamResponse
    assert len(rapidy_http.__all__) == 90
    assert 'SSEResponse' in rapidy_http.__all__
    assert 'SSEEvent' not in rapidy_http.__all__
    assert list(inspect.signature(StreamResponse.__init__).parameters)[1:] == [
        'body',
        'status',
        'headers',
        'content_type',
        'charset',
        'background',
    ]
    assert inspect.signature(StreamResponse.write_eof).parameters['data'].default == b''
    assert list(inspect.signature(SSEResponse.__init__).parameters)[1:] == [
        'events',
        'status',
        'headers',
        'retry',
        'background',
    ]


@pytest.mark.asyncio
async def test_e2e_iterative_imperative_and_http2_sse() -> None:
    @get('/stream')
    async def stream_handler() -> StreamResponse:
        async def chunks() -> AsyncIterator[str]:
            yield 'a'
            yield 'b'

        return StreamResponse(body=chunks(), headers={'content-length': '2'})

    @get('/imperative')
    async def imperative_handler(request: Request) -> StreamResponse:
        response = StreamResponse()
        await response.prepare(request)
        await response.write(b'a')
        await response.write_eof(b'z')
        return response

    @get('/sse')
    async def sse_handler() -> SSEResponse:
        async def events() -> AsyncIterator[str]:
            yield 'event'

        return SSEResponse(events())

    app = Rapidy(http_route_handlers=[stream_handler, imperative_handler, sse_handler])
    streamed = await run_http(app, '/stream')
    imperative = await run_http(app, '/imperative')
    h2_sse = await run_http(app, '/sse', http_version='2')

    assert [message['body'] for message in streamed[1:]] == [b'a', b'b', b'']
    assert 'content-length' not in decode_headers(streamed[0])
    assert sum(message['type'] == 'http.response.start' for message in imperative) == 1
    assert imperative[-1] == {'type': 'http.response.body', 'body': b'z', 'more_body': False}
    assert 'connection' not in decode_headers(h2_sse[0])


class StreamResource:
    pass


class StreamProvider(Provider):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    @provide(scope=Scope.REQUEST)
    async def resource(self) -> AsyncIterator[StreamResource]:
        self.events.append('created')
        try:
            yield StreamResource()
        finally:
            self.events.append('finalized')


@pytest.mark.asyncio
async def test_e2e_di_finalizer_after_last_frame_and_middleware_passthrough() -> None:
    events: list[str] = []
    seen: list[StreamResponse] = []

    @get('/stream')
    async def handler(resource: FromDI[StreamResource]) -> StreamResponse:
        assert isinstance(resource, StreamResource)

        async def chunks() -> AsyncIterator[bytes]:
            events.append('chunk')
            yield b'data'

        return StreamResponse(body=chunks())

    @middleware
    async def passthrough(request: Request, call_next: CallNext) -> Any:
        response = await call_next(request)
        assert isinstance(response, StreamResponse)
        seen.append(response)
        return response

    transport = FakeHTTPTransport()

    async def send(message: dict[str, Any]) -> None:
        await transport.send(message)
        if message.get('type') == 'http.response.body' and message.get('more_body') is False:
            events.append('last_frame')

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
    app = Rapidy(
        di_providers=[StreamProvider(events)],
        middlewares=[passthrough],
        http_route_handlers=[handler],
    )
    async with app.lifespan.ctx_manager():
        await app(scope, transport.receive, send)

    assert len(seen) == 1
    assert events == ['created', 'chunk', 'last_frame', 'finalized']


@pytest.mark.asyncio
async def test_e2e_disconnect_acloses_and_di_finalizer() -> None:
    events: list[str] = []
    generator_finalized = asyncio.Event()
    release = asyncio.Event()

    @post('/stream')
    async def handler(resource: FromDI[StreamResource]) -> StreamResponse:
        assert isinstance(resource, StreamResource)

        async def chunks() -> AsyncIterator[bytes]:
            try:
                yield b'first'
                await release.wait()
            finally:
                generator_finalized.set()

        return StreamResponse(body=chunks())

    app = Rapidy(di_providers=[StreamProvider(events)], http_route_handlers=[handler])
    transport = FakeHTTPTransport()
    transport.feed({'type': 'http.request', 'body': b'unread', 'more_body': True})
    scope: dict[str, Any] = {
        'type': 'http',
        'http_version': '1.1',
        'method': 'POST',
        'path': '/stream',
        'query_string': b'',
        'headers': [],
        'state': {},
    }
    async with app.lifespan.ctx_manager():
        task = asyncio.create_task(app(scope, transport.receive, transport.send))
        await transport.body_sent.wait()
        transport.feed({'type': 'http.request', 'body': b'', 'more_body': False})
        await asyncio.sleep(0)
        assert not task.done()
        transport.feed({'type': 'http.disconnect'})
        await task

    assert generator_finalized.is_set()
    assert events == ['created', 'finalized']
    task_names = {current.get_coro().__qualname__ for current in asyncio.all_tasks()}
    assert not any(name.endswith(('_listen_for_disconnect', '_iterate_and_send')) for name in task_names)


async def assert_live_sse(runtime: str) -> None:
    with live_server(runtime, 'tests.apps.sse_app:app') as base_url:
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=5) as client, client.stream('GET', f'{base_url}/sse') as response:
            assert response.status_code == 200
            assert response.headers['content-type'].startswith('text/event-stream')
            assert 'content-length' not in response.headers
            lines = response.aiter_lines()
            assert await anext(lines) == 'data: {"n": 0}'
            assert time.monotonic() - started < 3


@pytest.mark.asyncio
async def test_sse_live_granian() -> None:
    await assert_live_sse('granian')


@pytest.mark.asyncio
async def test_sse_live_uvicorn() -> None:
    await assert_live_sse('uvicorn')


@pytest.mark.asyncio
async def test_stream_live_granian() -> None:
    with live_server('granian', 'tests.apps.sse_app:app') as base_url:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f'{base_url}/stream')
    assert response.content == b'chunk-1chunk-2'
    assert 'content-length' not in response.headers
