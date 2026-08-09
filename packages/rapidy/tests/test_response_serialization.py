from __future__ import annotations

import json
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any
from urllib.request import (
    Request as URLRequest,
    urlopen,
)

import httpx
import pytest
from pydantic import BaseModel, Field
from rapidy_core.enums import Charset, ContentType

from rapidy import Rapidy
from rapidy.exceptions import HTTPNoContent, HTTPNotModified
from rapidy.http import delete, get, HTTPRouter
from rapidy.response import (
    DEFAULT_JSON_TYPES,
    DEFAULT_TEXT_PLAIN_TYPES,
    Response,
    ResponseDuplicateBodyError,
    ResponseEncodeError,
    StreamResponse,
)
from rapidy.responses import StreamResponse as ResponsesStreamResponse
from rapidy.version import SERVER_INFO
from tests.live_server import live_server


class Item(BaseModel):
    value: int
    optional: str | None = None
    aliased: str = Field('default', alias='alias')


class PublicUser(BaseModel):
    id: int
    email: str


class StoredUser(PublicUser):
    password_hash: str
    totp_secret: str


@dataclass
class DataItem:
    value: int


class TextEnum(Enum):
    value = 'enum-value'


async def request(app: Rapidy, method: str = 'GET', path: str = '/') -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://testserver',
    ) as client:
        return await client.request(method, path)


async def asgi_request(app: Rapidy, *, method: str = 'GET', path: str = '/') -> list[dict[str, Any]]:
    incoming = deque([{'type': 'http.request', 'body': b'', 'more_body': False}])
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        if incoming:
            return incoming.popleft()
        return {'type': 'http.disconnect'}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': method,
        'scheme': 'http',
        'path': path,
        'raw_path': path.encode(),
        'query_string': b'',
        'headers': (),
        'client': ('127.0.0.1', 1234),
        'server': ('testserver', 80),
    }
    async with app.lifespan.ctx_manager():
        await app(scope, receive, send)
    return sent


def decoded_headers(message: dict[str, Any]) -> list[tuple[str, str]]:
    return [(name.decode('latin-1').lower(), value.decode('latin-1')) for name, value in message['headers']]


@pytest.mark.parametrize(
    'value',
    [
        Item(value=1),
        {'value': 1},
        [1, 2],
        (1, 2),
        {1, 2},
        frozenset({1, 2}),
        DataItem(1),
    ],
)
def test_auto_json_content_type(value: Any) -> None:
    response = Response(value)
    assert response.content_type == ContentType.json.value
    assert json.loads(response.text or '')


@pytest.mark.parametrize('value', ['text', 1, 1.5, Decimal('1.5'), True, TextEnum.value])
def test_auto_text_content_type(value: Any) -> None:
    response = Response(value)
    assert response.content_type == ContentType.text_plain.value
    assert response.body is not None


def test_empty_and_bytes_contract() -> None:
    assert Response().body is None
    response = Response(b'raw')
    assert response.body == b'raw'
    assert response.content_type == ContentType.stream.value
    assert BaseModel in DEFAULT_JSON_TYPES
    assert str in DEFAULT_TEXT_PLAIN_TYPES


def test_duplicate_body_and_encode_errors() -> None:
    with pytest.raises(ResponseDuplicateBodyError, match='not allowed together'):
        Response(body=b'', text='')
    with pytest.raises(ResponseEncodeError, match='Encoding errors'):
        Response(object())


def test_explicit_content_type_dispatch_and_enums() -> None:
    json_response = Response('value', content_type=ContentType.json, charset=Charset.utf8)
    assert json_response.text == '"value"'
    assert json_response.content_type == 'application/json'
    assert json_response.charset == 'utf-8'

    text_response = Response({'value': 1}, content_type='text/plain')
    assert json.loads(text_response.text or '') == {'value': 1}

    vendor_response = Response({'value': 1}, content_type='application/vnd.api+json')
    assert json.loads(vendor_response.text or '') == {'value': 1}
    html_response = Response({'value': 1}, content_type='text/html')
    assert json.loads(html_response.text or '') == {'value': 1}


def test_mutable_assignment_order() -> None:
    response = Response({'first': 1})
    response.body = {'second': 2}
    assert json.loads(response.text or '') == {'second': 2}
    response.text = 'plain'
    assert response.text == 'plain'
    assert response.content_type == 'application/json'
    response.content_type = 'text/custom'
    assert response.body == b'plain'
    response.status = 201
    response.reason = 'Created'
    response.headers['x-test'] = 'yes'
    assert (response.status, response.reason, response.headers['x-test']) == (201, 'Created', 'yes')


def test_json_options_custom_encoder_and_noop_zlib() -> None:
    response = Response(
        Item(value=1),
        by_alias=True,
        exclude_none=True,
        exclude_defaults=True,
    )
    assert json.loads(response.text or '') == {'value': 1}

    class Custom:
        pass

    custom = Response(Custom(), custom_encoder={Custom: lambda _value: {'custom': True}})
    assert json.loads(custom.text or '') == {'custom': True}

    marked = Response({'value': 1}, json_encoder=lambda _value: 'encoded')
    assert marked.text == 'encoded'
    with ThreadPoolExecutor(max_workers=1) as executor:
        assert Response(zlib_executor=executor, zlib_executor_size=1).body is None


@pytest.mark.asyncio
async def test_send_headers_cookies_and_server_info() -> None:
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    response = Response({'value': 1})
    response.set_cookie('a', '1')
    response.set_cookie('b', '2', httponly=True)
    response.del_cookie('a')
    await response._send(send, server_info=SERVER_INFO)

    headers = decoded_headers(sent[0])
    assert ('content-type', 'application/json; charset=utf-8') in headers
    assert ('content-length', str(len(response.body or b''))) in headers
    assert ('server', SERVER_INFO) in headers
    cookies = [value for name, value in headers if name == 'set-cookie']
    assert len(cookies) == 2
    assert any('a=""' in value and 'Max-Age=0' in value and 'SameSite=Lax' in value for value in cookies)
    assert any('b=2' in value and 'HttpOnly' in value and 'SameSite=Lax' in value for value in cookies)

    with pytest.raises(ValueError, match='samesite'):
        response.set_cookie('bad', '1', samesite='invalid')


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [100, 199, 204, 304])
async def test_statuses_without_body(status: int) -> None:
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await Response('ignored', status=status)._send(send)
    assert 'content-length' not in dict(decoded_headers(sent[0]))
    assert sent[1]['body'] == b''


@pytest.mark.asyncio
async def test_route_serialization_validation_type_and_charset() -> None:
    @get('/cast')
    async def cast_result() -> int:
        return '7'  # type: ignore[return-value]

    @get('/raw', response_validate=False)
    async def raw_result() -> int:
        return 'raw'  # type: ignore[return-value]

    @get('/typed', response_type=Item)
    async def typed_result() -> dict[str, int]:
        return {'value': 3}

    @get('/invalid')
    async def invalid_result() -> int:
        return 'not-an-int'  # type: ignore[return-value]

    @get('/charset', response_charset=Charset.utf16)
    async def charset_result() -> str:
        return 'hello'

    app = Rapidy(http_route_handlers=[cast_result, raw_result, typed_result, invalid_result, charset_result])
    async with app.lifespan.ctx_manager():
        assert (await request(app, path='/cast')).text == '7'
        assert (await request(app, path='/raw')).text == 'raw'
        assert (await request(app, path='/typed')).json() == {'value': 3, 'optional': None, 'alias': 'default'}
        assert (await request(app, path='/invalid')).status_code == 500
        charset_response = await request(app, path='/charset')

    assert charset_response.headers['content-type'] == 'text/plain; charset=utf-16'
    assert charset_response.content == 'hello'.encode('utf-16')


@pytest.mark.asyncio
async def test_declared_response_contract_filters_runtime_subclass_fields() -> None:
    user = StoredUser(
        id=1,
        email='user@example.test',
        password_hash='secret-hash',  # noqa: S106
        totp_secret='secret-totp',  # noqa: S106
    )

    @get('/one')
    async def one() -> PublicUser:
        return user

    @get('/many')
    async def many() -> list[PublicUser]:
        return [user]

    @get('/raw', response_validate=False)
    async def raw() -> PublicUser:
        return user

    app = Rapidy(http_route_handlers=[one, many, raw])
    async with app.lifespan.ctx_manager():
        one_response = await request(app, path='/one')
        many_response = await request(app, path='/many')
        raw_response = await request(app, path='/raw')

    assert one_response.json() == {'id': 1, 'email': 'user@example.test'}
    assert many_response.json() == [{'id': 1, 'email': 'user@example.test'}]
    assert raw_response.json() == {
        'id': 1,
        'email': 'user@example.test',
        'password_hash': 'secret-hash',
        'totp_secret': 'secret-totp',
    }


@pytest.mark.asyncio
async def test_route_json_serialization_options() -> None:
    @get('/include', response_include_fields={'value', 'aliased'}, response_by_alias=False)
    async def include_result() -> Item:
        return Item(value=1)

    @get(
        '/exclude',
        response_exclude_fields={'optional'},
        response_exclude_defaults=True,
        response_exclude_none=True,
    )
    async def exclude_result() -> Item:
        return Item(value=2, alias='changed')

    @get('/unset', response_exclude_unset=True)
    async def unset_result() -> Item:
        return Item(value=3)

    class Custom:
        pass

    @get(
        '/custom',
        response_content_type=ContentType.json,
        response_custom_encoder={Custom: lambda _value: 'custom'},
        response_json_encoder=lambda value: json.dumps({'wrapped': value}),
    )
    async def custom_result() -> Any:
        return Custom()

    app = Rapidy(http_route_handlers=[include_result, exclude_result, unset_result, custom_result])
    async with app.lifespan.ctx_manager():
        assert (await request(app, path='/include')).json() == {'value': 1, 'aliased': 'default'}
        assert (await request(app, path='/exclude')).json() == {'value': 2, 'alias': 'changed'}
        assert (await request(app, path='/unset')).json() == {'value': 3}
        assert (await request(app, path='/custom')).json() == {'wrapped': 'custom'}


@pytest.mark.asyncio
async def test_no_body_http_exceptions_and_route_status() -> None:
    @delete('/route', status_code=204)
    async def no_content_route() -> str:
        return 'ignored'

    @get('/exception')
    async def no_content_exception() -> None:
        raise HTTPNoContent

    @get('/not-modified')
    async def not_modified() -> None:
        raise HTTPNotModified

    app = Rapidy(http_route_handlers=[no_content_route, no_content_exception, not_modified])
    for method, path, expected_status in (
        ('DELETE', '/route', 204),
        ('GET', '/exception', 204),
        ('GET', '/not-modified', 304),
    ):
        sent = await asgi_request(app, method=method, path=path)
        assert sent[0]['status'] == expected_status
        assert 'content-length' not in dict(decoded_headers(sent[0]))
        assert sent[1]['body'] == b''


@pytest.mark.asyncio
async def test_server_info_uses_matched_subapplication() -> None:
    @get('/child')
    async def child() -> str:
        return 'child'

    @get('/root')
    async def root() -> str:
        return 'root'

    router = HTTPRouter('/api', route_handlers=[child])
    router.application.server_info_in_response = True
    app = Rapidy(http_route_handlers=[root, router])
    assert ('server', SERVER_INFO) in decoded_headers((await asgi_request(app, path='/api/child'))[0])
    assert 'server' not in dict(decoded_headers((await asgi_request(app, path='/root'))[0]))

    router.application.server_info_in_response = False
    app.server_info_in_response = True
    assert 'server' not in dict(decoded_headers((await asgi_request(app, path='/api/child'))[0]))
    assert ('server', SERVER_INFO) in decoded_headers((await asgi_request(app, path='/root'))[0])


def test_stream_response_has_one_public_identity() -> None:
    assert StreamResponse is ResponsesStreamResponse
    assert not isinstance(Response(), StreamResponse)


def test_live_uvicorn_no_body_and_server_header() -> None:
    with live_server('uvicorn', 'tests.apps.response_contract:app') as base_url:
        no_content_request = URLRequest(f'{base_url}/no-content', method='DELETE')  # noqa: S310
        with urlopen(no_content_request, timeout=5) as response:  # noqa: S310
            assert response.status == 204
            assert response.read() == b''
            assert response.headers.get('content-length') is None
        with urlopen(f'{base_url}/server', timeout=5) as response:  # noqa: S310
            assert SERVER_INFO in response.headers.get_all('server', ())

    with (
        live_server('uvicorn', 'tests.apps.response_contract:default_app') as base_url,
        urlopen(f'{base_url}/server', timeout=5) as response,  # noqa: S310
    ):
        assert response.headers.get_all('server') == ['uvicorn']
