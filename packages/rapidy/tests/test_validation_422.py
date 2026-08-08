from __future__ import annotations

import json
from collections import Counter

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.exceptions import HTTPValidationFailure
from rapidy.http import Body, Cookie, get, Header, PathParam, post, QueryParam


class Item(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_validation_failure_body_schema_is_transport_stable() -> None:
    @post('/items')
    async def create(item: Item = Body()) -> str:
        return item.name

    app = Rapidy(http_route_handlers=[create])
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.post('/items', json={})

    assert response.status_code == 422
    assert response.headers['content-type'].startswith('application/json')
    errors = response.json()['errors']
    assert errors[0]['loc'] == ['body', 'name']
    assert errors[0].keys() == {'loc', 'msg', 'type'}


@pytest.mark.asyncio
async def test_validation_locations_cover_every_non_body_source() -> None:
    @get('/sources/{path_value}')
    async def sources(
        path_value: int = PathParam(),
        query_value: int = QueryParam(),
        header_value: int = Header(alias='x-value'),
        cookie_value: int = Cookie(),
    ) -> str:
        return 'never'

    app = Rapidy(http_route_handlers=[sources])
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.get(
            '/sources/bad?query_value=bad',
            headers={'x-value': 'bad'},
            cookies={'cookie_value': 'bad'},
        )

    assert response.status_code == 422
    locations = Counter(error['loc'][0] for error in response.json()['errors'])
    assert locations == Counter({'path': 1, 'query': 1, 'header': 1, 'cookie': 1})


def test_validation_failure_contract_is_customizable_and_normalized() -> None:
    error = {'loc': ('body',), 'msg': 'm', 'type': 't', 'input': 1, 'url': 'u'}

    class DetailFailure(HTTPValidationFailure):
        validation_failure_field_name = 'detail'

    failure = DetailFailure(errors=error)  # type: ignore[arg-type]

    assert json.loads(failure.text) == {'detail': [{'loc': ['body'], 'msg': 'm', 'type': 't', 'input': 1, 'url': 'u'}]}
    assert failure.validation_errors == [error]
