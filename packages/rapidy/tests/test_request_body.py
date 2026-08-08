from __future__ import annotations

import asyncio
from urllib.error import HTTPError
from urllib.request import (
    Request as URLRequest,
    urlopen,
)

import pytest
from httpx import ASGITransport, AsyncClient

from rapidy import Rapidy
from rapidy.exceptions import HTTPRequestEntityTooLarge
from tests.apps.echo_body import app as echo_app
from tests.live_server import live_server
from tests.request_factory import make_request


def test_query_cookies_content_type_and_cache_contract() -> None:
    request, _ = make_request(
        query_string=b'a=1&a=2&flag=',
        headers=(
            (b'cookie', b'a=1; b=2'),
            (b'content-type', b'text/html; charset=utf-8'),
        ),
    )

    assert request.query.getall('a') == ['1', '2']
    assert request.query['flag'] == ''
    assert dict(request.cookies) == {'a': '1', 'b': '2'}
    with pytest.raises(TypeError):
        request.cookies['c'] = '3'
    assert request.content_type == 'text/html'
    assert request.charset == 'utf-8'
    assert request._cache == {}


def test_defaults_and_body_exists_by_http_version() -> None:
    request, _ = make_request()
    assert request.content_type == 'application/octet-stream'
    assert request.charset is None
    assert request.cookies == {}
    assert request.query == {}
    assert request.body_exists is False

    request, _ = make_request(headers=((b'content-length', b'5'),))
    assert request.body_exists is True
    request, _ = make_request(headers=((b'content-length', b'0'),))
    assert request.body_exists is False
    request, _ = make_request(headers=((b'transfer-encoding', b'gzip, Chunked'),))
    assert request.body_exists is True
    request, _ = make_request(http_version='2', body_chunks=[b'data'])
    assert request.body_exists is True
    request, _ = make_request(http_version='2', headers=((b'content-length', b'0'),))
    assert request.body_exists is False


def test_client_max_size_follows_rebound_app() -> None:
    request, _ = make_request(app=Rapidy(client_max_size=7))
    assert request.client_max_size == 7
    request.app = Rapidy(client_max_size=11)
    assert request.client_max_size == 11


@pytest.mark.asyncio
async def test_read_is_one_shot_and_joins_empty_chunks() -> None:
    request, receive = make_request(body_chunks=[b'ab', b'', b'cd'])
    assert await request.read() == b'abcd'
    assert receive.calls == 3
    assert await request.read() == b'abcd'
    assert receive.calls == 3


@pytest.mark.asyncio
async def test_concurrent_first_read_consumes_receive_once() -> None:
    request, receive = make_request(body_chunks=[b'a', b'b'])
    results = await asyncio.gather(request.read(), request.read())
    assert results == [b'ab', b'ab']
    assert receive.calls == 2


@pytest.mark.asyncio
async def test_read_limit_is_checked_incrementally() -> None:
    request, receive = make_request(
        app=Rapidy(client_max_size=5),
        body_chunks=[b'123', b'456', b'not-read'],
    )
    with pytest.raises(HTTPRequestEntityTooLarge) as exc_info:
        await request.read()
    assert exc_info.value.max_size == 5
    assert exc_info.value.actual_size == 6
    assert receive.calls == 2


@pytest.mark.asyncio
async def test_disconnect_during_read_is_transport_error() -> None:
    request, _ = make_request(
        messages=[
            {'type': 'http.request', 'body': b'a', 'more_body': True},
            {'type': 'http.disconnect'},
        ]
    )
    with pytest.raises(ConnectionResetError):
        await request.read()


@pytest.mark.asyncio
async def test_text_json_and_http2_body() -> None:
    encoded = 'привет'.encode('cp1251')
    request, _ = make_request(
        headers=((b'content-type', b'text/plain; charset=windows-1251'),),
        body_chunks=[encoded],
    )
    assert await request.text() == 'привет'

    custom_calls: list[str] = []

    def custom_loads(value: str) -> dict[str, int]:
        custom_calls.append(value)
        return {'custom': 1}

    request, _ = make_request(body_chunks=[b'{"a": 1}'])
    assert await request.json() == {'a': 1}
    assert await request.json(loads=custom_loads) == {'custom': 1}
    assert custom_calls == ['{"a": 1}']

    request, _ = make_request(http_version='2', body_chunks=[b'h2'])
    assert request.body_exists is True
    assert await request.read() == b'h2'


@pytest.mark.asyncio
async def test_body_limit_renders_http_413() -> None:
    async with AsyncClient(transport=ASGITransport(app=echo_app), base_url='http://testserver') as client:
        accepted = await client.request('GET', '/echo', content=b'hello')
        rejected = await client.request('GET', '/echo', content=b'12345678901')

    assert accepted.status_code == 200
    assert accepted.text == 'hello'
    assert rejected.status_code == 413
    assert '10' in rejected.text
    assert '11' in rejected.text


@pytest.mark.parametrize('runtime', ['granian', 'uvicorn'])
def test_live_body_limit(runtime: str) -> None:
    with live_server(runtime, 'tests.apps.echo_body:app') as base_url:
        accepted_request = URLRequest(f'{base_url}/echo', data=b'hello', method='GET')  # noqa: S310
        with urlopen(accepted_request, timeout=5) as response:  # noqa: S310
            assert response.status == 200
            assert response.read() == b'hello'

        rejected_request = URLRequest(f'{base_url}/echo', data=b'12345678901', method='GET')  # noqa: S310
        with pytest.raises(HTTPError) as exc_info, urlopen(rejected_request, timeout=5):  # noqa: S310
            pass
        assert exc_info.value.code == 413
