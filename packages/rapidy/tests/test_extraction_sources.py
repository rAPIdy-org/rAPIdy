from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import (
    Request as URLRequest,
    urlopen,
)

import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
    Response as HTTPXResponse,
)
from multidict import CIMultiDictProxy, MultiDictProxy
from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.endpoint_handlers.http.attrs_extractor import RequestFieldAlreadyExistsError
from rapidy.http import Body, ContentType, Cookie, get, Header, PathParam, post, QueryParam, Request, Response
from rapidy.request import FileField
from tests.live_server import live_server


async def request(app: Rapidy, method: str, path: str, **kwargs: Any) -> HTTPXResponse:
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        return await client.request(method, path, **kwargs)


class Payload(BaseModel):
    count: int


@pytest.mark.asyncio
async def test_all_request_sources_are_extracted_and_validated() -> None:
    observed: dict[str, Any] = {}

    @post('/items/{item_id}')
    async def create_item(
        payload: Payload = Body(),
        token: str = Header(alias='x-token'),
        item_id: int = PathParam(),
        page: int = QueryParam(alias='q'),
        session: str = Cookie(),
    ) -> str:
        observed.update(
            payload=payload,
            token=token,
            item_id=item_id,
            page=page,
            session=session,
        )
        return 'ok'

    response = await request(
        Rapidy(http_route_handlers=[create_item]),
        'POST',
        '/items/7?q=3',
        json={'count': '2'},
        headers={'x-token': 'secret'},
        cookies={'session': 'cookie-value'},
    )

    assert response.status_code == 200
    assert response.text == 'ok'
    assert observed == {
        'payload': Payload(count=2),
        'token': 'secret',
        'item_id': 7,
        'page': 3,
        'session': 'cookie-value',
    }


@pytest.mark.asyncio
async def test_content_type_errors_wildcards_and_disabled_check() -> None:
    @post('/json')
    async def json_body(payload: Payload = Body()) -> str:
        return str(payload.count)

    @post('/application-wildcard')
    async def application_wildcard(data: bytes = Body(content_type='application/*')) -> str:
        return data.decode()

    @post('/all-wildcard')
    async def all_wildcard(data: bytes = Body(content_type='*/*')) -> str:
        return data.decode()

    @post('/unchecked')
    async def unchecked(payload: Payload = Body(check_content_type=False)) -> str:
        return str(payload.count)

    app = Rapidy(
        http_route_handlers=[json_body, application_wildcard, all_wildcard, unchecked],
    )
    wrong = await request(app, 'POST', '/json', content=b'{"count": 1}', headers={'content-type': 'text/plain'})
    empty = await request(app, 'POST', '/json', content=b'{"count": 1}', headers={'content-type': ''})
    application = await request(
        app,
        'POST',
        '/application-wildcard',
        content=b'app',
        headers={'content-type': 'application/vnd.api+json'},
    )
    any_type = await request(
        app,
        'POST',
        '/all-wildcard',
        content=b'any',
        headers={'content-type': 'image/png'},
    )
    unchecked_response = await request(
        app,
        'POST',
        '/unchecked',
        content=b'{"count": 4}',
        headers={'content-type': 'text/plain'},
    )

    wrong_error = wrong.json()['errors'][0]
    assert wrong.status_code == 422
    assert wrong_error['type'] == 'ExtractError'
    assert wrong_error['loc'] == ['body']
    assert wrong_error['msg'] == (
        'Failed to extract body data: Expected Content-Type `application/json` not `text/plain`'
    )
    assert empty.status_code == 422
    assert empty.json()['errors'][0]['msg'] == (
        'Failed to extract body data: '
        '`Content-Type` header cannot be empty. Expected: `application/json`'
    )
    assert application.text == 'app'
    assert any_type.text == 'any'
    assert unchecked_response.text == '4'


@pytest.mark.asyncio
async def test_form_and_multipart_extraction() -> None:
    observed: dict[str, Any] = {}

    @post('/form')
    async def form(data: Any = Body(content_type=ContentType.x_www_form)) -> str:
        assert isinstance(data, MultiDictProxy)
        observed['form'] = data.getall('a')
        return 'form'

    @post('/multipart')
    async def multipart(data: Any = Body(content_type=ContentType.m_part_form_data)) -> str:
        assert isinstance(data, MultiDictProxy)
        uploaded = data['upload']
        assert isinstance(uploaded, FileField)
        assert uploaded.name == 'upload'
        assert uploaded.filename == 'f.bin'
        assert uploaded.file.read() == b'file-body'
        assert uploaded.content_type == 'application/pdf'
        assert isinstance(uploaded.headers, CIMultiDictProxy)
        uploaded.file.close()
        observed['field'] = data['field']
        return 'multipart'

    app = Rapidy(http_route_handlers=[form, multipart])
    form_response = await request(
        app,
        'POST',
        '/form',
        content=b'a=1&a=2',
        headers={'content-type': ContentType.x_www_form},
    )
    multipart_response = await request(
        app,
        'POST',
        '/multipart',
        data={'field': 'value'},
        files={'upload': ('f.bin', b'file-body', 'application/pdf')},
    )

    assert form_response.status_code == 200
    assert multipart_response.status_code == 200
    assert observed == {'form': ['1', '2'], 'field': 'value'}


@pytest.mark.asyncio
async def test_multipart_structure_error_is_normalized() -> None:
    @post('/multipart')
    async def multipart(data: Any = Body(content_type=ContentType.m_part_form_data)) -> str:
        return str(data)

    response = await request(
        Rapidy(http_route_handlers=[multipart]),
        'POST',
        '/multipart',
        content=b'x',
        headers={'content-type': ContentType.m_part_form_data},
    )

    error = response.json()['errors'][0]
    assert response.status_code == 422
    assert error['loc'] == ['body']
    assert error['type'] == 'ExtractError'
    assert error['msg'] == (
        'Failed to extract body data as Multipart: '
        'boundary missed for Content-Type: multipart/form-data'
    )


@pytest.mark.asyncio
async def test_body_is_read_once_even_when_handler_reads_again() -> None:
    @post('/raw')
    async def raw(request: Request, data: bytes = Body(content_type=ContentType.stream)) -> str:
        assert await request.read() == data
        return data.decode()

    app = Rapidy(http_route_handlers=[raw])
    messages = [
        {'type': 'http.request', 'body': b'ab', 'more_body': True},
        {'type': 'http.request', 'body': b'cd', 'more_body': False},
    ]
    receive_calls = 0
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        nonlocal receive_calls
        message = messages[receive_calls]
        receive_calls += 1
        return message

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await app(
        {
            'type': 'http',
            'http_version': '1.1',
            'method': 'POST',
            'path': '/raw',
            'query_string': b'',
            'headers': [(b'content-type', b'application/octet-stream'), (b'content-length', b'4')],
            'state': {},
        },
        receive,
        send,
    )

    assert receive_calls == 2
    assert sent[-1]['body'] == b'abcd'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('path', 'kwargs'),
    [
        ('/raw', {'content': b'123456'}),
        ('/form', {'content': b'a=123456', 'headers': {'content-type': ContentType.x_www_form}}),
        ('/multipart', {'files': {'upload': ('f.bin', b'x', 'application/octet-stream')}}),
    ],
)
async def test_client_max_size_survives_extraction(path: str, kwargs: dict[str, Any]) -> None:
    @post('/raw')
    async def raw(data: bytes = Body(content_type='*/*')) -> str:
        return data.decode()

    @post('/form')
    async def form(data: Any = Body(content_type=ContentType.x_www_form)) -> str:
        return str(data)

    @post('/multipart')
    async def multipart(data: Any = Body(content_type=ContentType.m_part_form_data)) -> str:
        return str(data)

    response = await request(
        Rapidy(http_route_handlers=[raw, form, multipart], client_max_size=5),
        'POST',
        path,
        **kwargs,
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_request_injection_annotated_and_implicit() -> None:
    @get('/annotated')
    async def annotated(request: Request) -> str:
        return request.path

    @get('/implicit')
    async def implicit(request) -> str:
        return request.path

    app = Rapidy(http_route_handlers=[annotated, implicit])
    annotated_response = await request(app, 'GET', '/annotated')
    implicit_response = await request(app, 'GET', '/implicit')

    assert annotated_response.text == '/annotated'
    assert implicit_response.text == '/implicit'

    @get('/duplicate')
    async def duplicate(first, second: Request) -> str:
        return 'never'

    with pytest.raises(RequestFieldAlreadyExistsError):
        Rapidy(http_route_handlers=[duplicate])


@pytest.mark.asyncio
async def test_current_response_placeholder_is_injected() -> None:
    @get('/response', status_code=201)
    async def injected(response: Response) -> None:
        response.text = 'prepared'

    response = await request(Rapidy(http_route_handlers=[injected]), 'GET', '/response')

    assert response.status_code == 201
    assert response.text == 'prepared'


@pytest.mark.asyncio
async def test_invalid_json_is_a_validation_failure() -> None:
    @post('/json')
    async def json_body(payload: Payload = Body()) -> str:
        return str(payload.count)

    response = await request(
        Rapidy(http_route_handlers=[json_body]),
        'POST',
        '/json',
        content=b'{"oops"',
        headers={'content-type': ContentType.json},
    )

    assert response.status_code == 422
    assert response.json()['errors'][0]['msg'].startswith('Failed to extract body data as Json: ')


def test_live_uvicorn_extraction_pipeline() -> None:
    with live_server('uvicorn', 'tests.apps.extraction:app') as base_url:
        valid_request = URLRequest(  # noqa: S310
            f'{base_url}/items?q=2',
            data=b'{"name": "book"}',
            headers={'content-type': ContentType.json},
            method='POST',
        )
        with urlopen(valid_request, timeout=5) as response:  # noqa: S310
            assert response.status == 200
            assert response.read() == b'book:2'

        missing_request = URLRequest(  # noqa: S310
            f'{base_url}/items?q=2',
            data=b'{}',
            headers={'content-type': ContentType.json},
            method='POST',
        )
        with pytest.raises(HTTPError) as missing_error, urlopen(missing_request, timeout=5):  # noqa: S310
            pass
        assert missing_error.value.code == 422
        assert json.loads(missing_error.value.read())['errors'][0]['loc'] == ['body', 'name']

        wrong_type_request = URLRequest(  # noqa: S310
            f'{base_url}/items?q=2',
            data=b'x',
            headers={'content-type': 'text/plain'},
            method='POST',
        )
        with pytest.raises(HTTPError) as wrong_type_error, urlopen(wrong_type_request, timeout=5):  # noqa: S310
            pass
        assert wrong_type_error.value.code == 422
        assert json.loads(wrong_type_error.value.read())['errors'][0]['msg'].startswith(
            'Failed to extract body data: Expected Content-Type',
        )
