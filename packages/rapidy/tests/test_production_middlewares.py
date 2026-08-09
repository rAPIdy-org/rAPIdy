from __future__ import annotations

import asyncio
import gzip
from collections.abc import AsyncIterator, Callable
from concurrent.futures import Executor, Future
from dataclasses import dataclass
from typing import Any

import pytest
from multidict import CIMultiDict

from rapidy import Rapidy
from rapidy.http import get, Request, Response, SSEResponse, StreamResponse
from rapidy.middlewares import (
    CompressionMiddleware,
    CORSMiddleware,
    get_request_context,
    get_request_id,
    GZipMiddleware,
    HTTPSRedirectMiddleware,
    ProxyHeadersMiddleware,
    RequestIDMiddleware,
    TrustedHostMiddleware,
)


@dataclass(slots=True)
class RawResponse:
    status: int
    headers: CIMultiDict[str]
    body: bytes


class InlineExecutor(Executor):
    def __init__(self) -> None:
        self.calls = 0

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Future[Any]:
        self.calls += 1
        future: Future[Any] = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:
            future.set_exception(exc)
        return future


async def request_app(
    app: Rapidy,
    path: str = '/',
    *,
    method: str = 'GET',
    scheme: str = 'http',
    query: bytes = b'',
    headers: list[tuple[bytes, bytes]] | None = None,
    client: tuple[str, int] = ('127.0.0.1', 50000),
) -> RawResponse:
    sent: list[dict[str, Any]] = []
    incoming: list[dict[str, Any]] = [{'type': 'http.request', 'body': b'', 'more_body': False}]

    async def receive() -> dict[str, Any]:
        if incoming:
            return incoming.pop(0)
        await _wait_forever()
        raise AssertionError

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    request_headers = [(b'host', b'testserver')]
    if headers is not None:
        request_headers = headers
    scope: dict[str, Any] = {
        'type': 'http',
        'http_version': '1.1',
        'method': method,
        'scheme': scheme,
        'path': path,
        'raw_path': path.encode('ascii'),
        'query_string': query,
        'headers': request_headers,
        'client': client,
        'server': ('testserver', 80),
        'state': {},
    }
    await app(scope, receive, send)
    start = next(message for message in sent if message['type'] == 'http.response.start')
    response_headers = CIMultiDict(
        (bytes(name).decode('latin-1'), bytes(value).decode('latin-1')) for name, value in start['headers']
    )
    body = b''.join(bytes(message.get('body', b'')) for message in sent if message['type'] == 'http.response.body')
    return RawResponse(start['status'], response_headers, body)


async def _wait_forever() -> None:
    await asyncio.Event().wait()


@pytest.mark.asyncio
async def test_cors_simple_errors_preflight_and_pna() -> None:
    @get('/ok')
    async def handler() -> str:
        return 'ok'

    cors = CORSMiddleware(
        allow_origins=('https://client.example',),
        allow_methods=('GET', 'POST'),
        allow_headers=('authorization', 'x-token'),
        expose_headers=('X-Result',),
        allow_credentials=True,
        allow_private_network=True,
    )
    app = Rapidy(middlewares=[cors], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        simple = await request_app(
            app,
            '/ok',
            headers=[(b'host', b'testserver'), (b'origin', b'https://client.example')],
        )
        missing = await request_app(
            app,
            '/missing',
            headers=[(b'host', b'testserver'), (b'origin', b'https://client.example')],
        )
        preflight = await request_app(
            app,
            '/anything',
            method='OPTIONS',
            headers=[
                (b'host', b'testserver'),
                (b'origin', b'https://client.example'),
                (b'access-control-request-method', b'POST'),
                (b'access-control-request-headers', b'X-Token, Authorization'),
                (b'access-control-request-private-network', b'true'),
            ],
        )
        denied = await request_app(
            app,
            '/anything',
            method='OPTIONS',
            headers=[
                (b'host', b'testserver'),
                (b'origin', b'https://evil.example'),
                (b'access-control-request-method', b'POST'),
            ],
        )
        duplicate_origin = await request_app(
            app,
            '/ok',
            headers=[
                (b'host', b'testserver'),
                (b'origin', b'https://client.example'),
                (b'origin', b'https://evil.example'),
            ],
        )

    assert simple.headers['access-control-allow-origin'] == 'https://client.example'
    assert simple.headers['access-control-allow-credentials'] == 'true'
    assert simple.headers['access-control-expose-headers'] == 'X-Result'
    assert 'Origin' in simple.headers['vary']
    assert missing.status == 404
    assert missing.headers['access-control-allow-origin'] == 'https://client.example'
    assert preflight.status == 204
    assert preflight.body == b''
    assert preflight.headers['access-control-allow-private-network'] == 'true'
    assert preflight.headers['access-control-allow-headers'] == 'authorization, x-token'
    assert denied.status == 400
    assert 'access-control-allow-origin' not in denied.headers
    assert 'access-control-allow-origin' not in duplicate_origin.headers


def test_cors_rejects_unsafe_wildcard_credentials_and_bad_fields() -> None:
    with pytest.raises(ValueError, match='credentialed CORS'):
        CORSMiddleware(allow_origins=('*',), allow_credentials=True)
    with pytest.raises(ValueError, match='invalid HTTP field name'):
        CORSMiddleware(allow_headers=('bad header',))
    with pytest.raises(ValueError, match='invalid HTTP field name'):
        CORSMiddleware(allow_methods=('GET\r\nInjected',))
    with pytest.raises(ValueError, match='invalid serialized origin'):
        CORSMiddleware(allow_origins=('https://example.com/path',))


@pytest.mark.asyncio
async def test_cors_wildcard_and_regex_contract() -> None:
    @get('/')
    async def handler() -> str:
        return 'ok'

    wildcard_app = Rapidy(middlewares=[CORSMiddleware(allow_origins=('*',))], http_route_handlers=[handler])
    regex_app = Rapidy(
        middlewares=[CORSMiddleware(allow_origin_regex=r'https://[a-z]+\.example')],
        http_route_handlers=[handler],
    )
    async with wildcard_app.lifespan.ctx_manager(), regex_app.lifespan.ctx_manager():
        wildcard = await request_app(wildcard_app, headers=[(b'host', b'test'), (b'origin', b'https://anywhere')])
        regex = await request_app(regex_app, headers=[(b'host', b'test'), (b'origin', b'https://api.example')])
    assert wildcard.headers['access-control-allow-origin'] == '*'
    assert 'vary' not in wildcard.headers
    assert regex.headers['access-control-allow-origin'] == 'https://api.example'


@pytest.mark.asyncio
async def test_trusted_host_and_https_redirect() -> None:
    @get('/items')
    async def handler() -> str:
        return 'ok'

    app = Rapidy(
        middlewares=[TrustedHostMiddleware(('api.example', '*.service.example'))],
        http_route_handlers=[handler],
    )
    redirect_app = Rapidy(
        middlewares=[TrustedHostMiddleware(('www.example.com',)), HTTPSRedirectMiddleware(('www.example.com',))],
        http_route_handlers=[handler],
    )
    async with app.lifespan.ctx_manager(), redirect_app.lifespan.ctx_manager():
        allowed = await request_app(app, '/items', headers=[(b'host', b'api.example:8080')])
        wildcard = await request_app(app, '/items', headers=[(b'host', b'v1.service.example')])
        rejected = await request_app(app, '/items', headers=[(b'host', b'evil.example')])
        duplicate = await request_app(app, '/items', headers=[(b'host', b'api.example'), (b'host', b'evil')])
        www = await request_app(redirect_app, '/items', query=b'a=1', headers=[(b'host', b'example.com:8080')])
        https = await request_app(
            redirect_app,
            '/items',
            scheme='https',
            headers=[(b'host', b'www.example.com')],
        )
        poisoned = await request_app(
            redirect_app,
            '/items',
            headers=[(b'host', b'evil.example')],
        )
    assert allowed.status == wildcard.status == 200
    assert rejected.status == duplicate.status == 400
    assert www.status == 307
    assert www.headers['location'] == 'http://www.example.com:8080/items?a=1'
    assert https.status == 200
    assert poisoned.status == 400


def test_trusted_host_configuration_is_validated() -> None:
    with pytest.raises(ValueError, match='at least one'):
        TrustedHostMiddleware(())
    with pytest.raises(ValueError, match='Wildcard host patterns'):
        TrustedHostMiddleware(('api.*.example',))
    with pytest.raises(ValueError, match='cannot be combined'):
        TrustedHostMiddleware(('*', 'example.com'))
    with pytest.raises(ValueError, match='at least one'):
        HTTPSRedirectMiddleware(())
    with pytest.raises(ValueError, match='cannot trust the wildcard'):
        HTTPSRedirectMiddleware(('*',))


@pytest.mark.asyncio
async def test_proxy_headers_require_a_trusted_peer_and_stop_at_trust_boundary() -> None:
    @get('/')
    async def handler(request: Request) -> str:
        client = request.scope.get('client')
        return f'{request.scope.get("scheme")}|{request.headers.get("host")}|{client[0]}'

    proxy = ProxyHeadersMiddleware(('10.0.0.0/8',))
    app = Rapidy(middlewares=[proxy], http_route_handlers=[handler])
    forwarded_headers = [
        (b'host', b'internal:8000'),
        (b'x-forwarded-for', b'198.51.100.7, 10.0.0.3'),
        (b'x-forwarded-proto', b'https'),
        (b'x-forwarded-host', b'api.example:8443'),
    ]
    async with app.lifespan.ctx_manager():
        trusted = await request_app(app, headers=forwarded_headers, client=('10.0.0.4', 5000))
        untrusted = await request_app(app, headers=forwarded_headers, client=('203.0.113.4', 5000))
        standardized = await request_app(
            app,
            headers=[
                (b'host', b'internal'),
                (b'forwarded', b'for=198.51.100.8;proto=https;host="public.example"'),
            ],
            client=('10.0.0.4', 5000),
        )
    assert trusted.body == b'https|api.example:8443|198.51.100.7'
    assert untrusted.body == b'http|internal:8000|203.0.113.4'
    assert standardized.body == b'https|public.example|198.51.100.8'


def test_proxy_headers_reject_empty_or_invalid_trust_configuration() -> None:
    with pytest.raises(ValueError, match='at least one'):
        ProxyHeadersMiddleware(())
    with pytest.raises(ValueError, match='does not appear to be'):
        ProxyHeadersMiddleware(('*',))
    with pytest.raises(ValueError, match='headers must be'):
        ProxyHeadersMiddleware(('127.0.0.1',), headers='invalid')  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_request_id_propagation_errors_and_stream_context() -> None:
    seen: list[str | None] = []

    @get('/context')
    async def context_handler(request: Request) -> str:
        context = get_request_context()
        assert context is not None
        assert request.state.request_context is context
        return f'{request.state.request_id}|{context.method}|{context.path}'

    @get('/stream')
    async def stream_handler() -> StreamResponse:
        async def chunks() -> AsyncIterator[str]:
            seen.append(get_request_id())
            yield 'stream'

        return StreamResponse(chunks(), content_type='text/plain')

    middleware = RequestIDMiddleware(generator=lambda: 'generated-id')
    app = Rapidy(middlewares=[middleware], http_route_handlers=[context_handler, stream_handler])
    async with app.lifespan.ctx_manager():
        propagated = await request_app(
            app,
            '/context',
            headers=[(b'host', b'test'), (b'x-request-id', b'client-id')],
        )
        generated = await request_app(
            app,
            '/context',
            headers=[(b'host', b'test'), (b'x-request-id', b'bad id')],
        )
        missing = await request_app(app, '/missing')
        stream = await request_app(app, '/stream')
    assert propagated.body == b'client-id|GET|/context'
    assert propagated.headers['x-request-id'] == 'client-id'
    assert generated.headers['x-request-id'] == 'generated-id'
    assert missing.status == 404
    assert missing.headers['x-request-id'] == 'generated-id'
    assert stream.body == b'stream'
    assert seen == ['generated-id']
    assert get_request_context() is None

    invalid_generator = Rapidy(middlewares=[RequestIDMiddleware(generator=lambda: 1)])  # type: ignore[arg-type,return-value]
    async with invalid_generator.lifespan.ctx_manager():
        invalid_response = await request_app(invalid_generator)
    assert invalid_response.status == 500


@pytest.mark.asyncio
async def test_request_id_is_added_before_imperative_stream_prepare() -> None:
    @get('/')
    async def handler(request: Request) -> StreamResponse:
        response = StreamResponse(content_type='text/plain')
        await response.prepare(request)
        await response.write_eof(b'ok')
        return response

    app = Rapidy(middlewares=[RequestIDMiddleware(generator=lambda: 'imperative')], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        response = await request_app(app)
    assert response.headers['x-request-id'] == 'imperative'
    assert response.body == b'ok'


@pytest.mark.asyncio
async def test_production_hooks_cross_mounts_and_keep_concurrent_context_isolated() -> None:
    generated = iter(('request-a', 'request-b'))

    @get('/value')
    async def handler() -> str:
        before = get_request_id()
        await asyncio.sleep(0)
        assert get_request_id() == before
        return str(before) * 100

    child = Rapidy(http_route_handlers=[handler])
    app = Rapidy(
        middlewares=[
            RequestIDMiddleware(generator=lambda: next(generated)),
            CORSMiddleware(allow_origins=('https://client.example',)),
            GZipMiddleware(minimum_size=1),
        ],
    )
    app.add_subapp('/api', child)
    headers = [
        (b'host', b'test'),
        (b'origin', b'https://client.example'),
        (b'accept-encoding', b'gzip'),
    ]
    async with app.lifespan.ctx_manager():
        first, second = await asyncio.gather(
            request_app(app, '/api/value', headers=headers),
            request_app(app, '/api/value', headers=headers),
        )
    assert {first.headers['x-request-id'], second.headers['x-request-id']} == {'request-a', 'request-b'}
    for response in (first, second):
        assert response.headers['access-control-allow-origin'] == 'https://client.example'
        assert response.headers['content-encoding'] == 'gzip'
        assert gzip.decompress(response.body) == response.headers['x-request-id'].encode() * 100


@pytest.mark.asyncio
async def test_gzip_buffered_negotiation_and_header_contract() -> None:
    executor = InlineExecutor()

    @get('/')
    async def handler() -> Response:
        return Response(
            'compress me ' * 100,
            headers={'vary': 'Origin', 'etag': '"source"', 'content-md5': 'obsolete'},
            content_type='text/plain',
            zlib_executor=executor,
            zlib_executor_size=1,
        )

    app = Rapidy(middlewares=[GZipMiddleware(minimum_size=10)], http_route_handlers=[handler])
    async with app.lifespan.ctx_manager():
        compressed = await request_app(app, headers=[(b'host', b'test'), (b'accept-encoding', b'gzip')])
        identity = await request_app(app, headers=[(b'host', b'test')])
    assert compressed.headers['content-encoding'] == 'gzip'
    assert compressed.headers['vary'] == 'Origin, Accept-Encoding'
    assert compressed.headers['content-length'] == str(len(compressed.body))
    assert compressed.headers['etag'] == 'W/"source"'
    assert 'content-md5' not in compressed.headers
    assert gzip.decompress(compressed.body) == b'compress me ' * 100
    assert executor.calls == 1
    assert 'content-encoding' not in identity.headers
    assert identity.headers['vary'] == 'Origin, Accept-Encoding'
    assert identity.body == b'compress me ' * 100


@pytest.mark.asyncio
async def test_compression_brotli_quality_negotiation() -> None:
    brotli = pytest.importorskip('brotli')

    @get('/')
    async def handler() -> Response:
        return Response(b'payload ' * 100, content_type='application/json')

    app = Rapidy(
        middlewares=[CompressionMiddleware(algorithms=('br', 'gzip'), minimum_size=1)],
        http_route_handlers=[handler],
    )
    async with app.lifespan.ctx_manager():
        brotli_response = await request_app(
            app,
            headers=[(b'host', b'test'), (b'accept-encoding', b'gzip;q=0.5, br;q=1')],
        )
        gzip_response = await request_app(
            app,
            headers=[(b'host', b'test'), (b'accept-encoding', b'gzip;q=1, br;q=0')],
        )
    assert brotli_response.headers['content-encoding'] == 'br'
    assert brotli.decompress(brotli_response.body) == b'payload ' * 100
    assert gzip_response.headers['content-encoding'] == 'gzip'


@pytest.mark.asyncio
async def test_streaming_compression_and_safety_exclusions() -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b'a' * 100
        yield b'b' * 100

    @get('/stream')
    async def stream_handler() -> StreamResponse:
        return StreamResponse(chunks(), content_type='text/plain', headers={'content-length': '200'})

    @get('/sse')
    async def sse_handler() -> SSEResponse:
        async def events() -> AsyncIterator[str]:
            yield 'event'

        return SSEResponse(events())

    @get('/encoded')
    async def encoded_handler() -> Response:
        return Response(b'already', content_type='application/json', headers={'content-encoding': 'custom'})

    @get('/partial')
    async def partial_handler() -> Response:
        return Response(b'partial', status=206, content_type='text/plain', headers={'content-range': 'bytes 0-6/7'})

    @get('/binary')
    async def binary_handler() -> Response:
        return Response(b'\x00' * 2000, content_type='application/octet-stream')

    app = Rapidy(
        middlewares=[GZipMiddleware(minimum_size=1000)],
        http_route_handlers=[stream_handler, sse_handler, encoded_handler, partial_handler, binary_handler],
    )
    accept = [(b'host', b'test'), (b'accept-encoding', b'gzip')]
    async with app.lifespan.ctx_manager():
        stream = await request_app(app, '/stream', headers=accept)
        sse = await request_app(app, '/sse', headers=accept)
        encoded = await request_app(app, '/encoded', headers=accept)
        partial = await request_app(app, '/partial', headers=accept)
        binary = await request_app(app, '/binary', headers=accept)
        ranged = await request_app(app, '/stream', headers=[*accept, (b'range', b'bytes=0-10')])
    assert stream.headers['content-encoding'] == 'gzip'
    assert 'content-length' not in stream.headers
    assert gzip.decompress(stream.body) == b'a' * 100 + b'b' * 100
    assert 'content-encoding' not in sse.headers
    assert encoded.headers['content-encoding'] == 'custom'
    assert 'content-encoding' not in partial.headers
    assert 'content-encoding' not in binary.headers
    assert 'content-encoding' not in ranged.headers
