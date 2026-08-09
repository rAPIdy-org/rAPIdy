from __future__ import annotations

from pydantic import BaseModel, Field

from rapidy import Rapidy
from rapidy.http import get, Header, Headers, QueryParam, QueryParams
from rapidy.testing import TestClient


class QueryModel(BaseModel):
    tags: list[int] = Field(alias='tag')
    page: int


class HeaderModel(BaseModel):
    modes: list[str] = Field(alias='X-Mode')
    request_id: str = Field(alias='X-Request-ID')


def test_repeated_values_are_collections_only_for_collection_annotations() -> None:
    @get('/collections')
    async def collections(
        tags: list[int] = QueryParam(alias='tag'),
        modes: tuple[str, ...] = Header(alias='X-Mode'),
        raw: list[str] = QueryParam(alias='raw', validate=False),
    ) -> dict[str, object]:
        return {'tags': tags, 'modes': modes, 'raw': raw}

    app = Rapidy(http_route_handlers=[collections])
    with TestClient(app) as client:
        response = client.get(
            '/collections',
            params=[('tag', '1'), ('tag', '2'), ('raw', 'a'), ('raw', 'b')],
            headers=[('X-Mode', 'fast'), ('X-Mode', 'safe')],
        )

    assert response.status_code == 200
    assert response.json() == {
        'tags': [1, 2],
        'modes': ['fast', 'safe'],
        'raw': ['a', 'b'],
    }


def test_repeated_scalar_query_and_header_values_are_rejected() -> None:
    @get('/scalar')
    async def scalar(
        page: int = QueryParam(),
        mode: str = Header(alias='X-Mode'),
    ) -> str:
        return f'{page}:{mode}'

    app = Rapidy(http_route_handlers=[scalar])
    with TestClient(app) as client:
        query = client.get(
            '/scalar',
            params=[('page', '1'), ('page', '2')],
            headers={'X-Mode': 'safe'},
        )
        header = client.get(
            '/scalar?page=1',
            headers=[('X-Mode', 'safe'), ('X-Mode', 'unsafe')],
        )

    assert query.status_code == header.status_code == 422
    assert query.json()['errors'][0] == {
        'type': 'duplicate_parameter',
        'loc': ['query', 'page'],
        'msg': "Multiple values are not allowed for scalar parameter 'page'",
    }
    assert header.json()['errors'][0] == {
        'type': 'duplicate_parameter',
        'loc': ['header', 'X-Mode'],
        'msg': "Multiple values are not allowed for scalar parameter 'X-Mode'",
    }


def test_plural_models_apply_the_same_type_directed_rules() -> None:
    @get('/models')
    async def models(
        query: QueryModel = QueryParams(),
        headers: HeaderModel = Headers(),
    ) -> dict[str, object]:
        return {
            'tags': query.tags,
            'page': query.page,
            'modes': headers.modes,
            'request_id': headers.request_id,
        }

    app = Rapidy(http_route_handlers=[models])
    with TestClient(app) as client:
        accepted = client.get(
            '/models',
            params=[('tag', '1'), ('tag', '2'), ('page', '3')],
            headers=[
                ('X-Mode', 'fast'),
                ('X-Mode', 'safe'),
                ('X-Request-ID', 'one'),
            ],
        )
        duplicate_query = client.get(
            '/models',
            params=[('tag', '1'), ('page', '2'), ('page', '3')],
            headers=[('X-Mode', 'safe'), ('X-Request-ID', 'one')],
        )
        duplicate_header = client.get(
            '/models',
            params=[('tag', '1'), ('page', '2')],
            headers=[
                ('X-Mode', 'safe'),
                ('X-Request-ID', 'one'),
                ('X-Request-ID', 'two'),
            ],
        )

    assert accepted.status_code == 200
    assert accepted.json() == {
        'tags': [1, 2],
        'page': 3,
        'modes': ['fast', 'safe'],
        'request_id': 'one',
    }
    assert duplicate_query.status_code == duplicate_header.status_code == 422
    assert duplicate_query.json()['errors'][0]['loc'] == ['query', 'page']
    assert duplicate_query.json()['errors'][0]['type'] == 'duplicate_parameter'
    assert duplicate_header.json()['errors'][0]['loc'] == ['header', 'X-Request-ID']
    assert duplicate_header.json()['errors'][0]['type'] == 'duplicate_parameter'


def test_plural_mapping_value_annotation_controls_repetitions() -> None:
    @get('/lists')
    async def lists(query: dict[str, list[str]] = QueryParams()) -> dict[str, list[str]]:
        return query

    @get('/scalars')
    async def scalars(query: dict[str, str] = QueryParams()) -> dict[str, str]:
        return query

    app = Rapidy(http_route_handlers=[lists, scalars])
    with TestClient(app) as client:
        accepted = client.get('/lists', params=[('tag', 'one'), ('tag', 'two')])
        rejected = client.get('/scalars', params=[('tag', 'one'), ('tag', 'two')])

    assert accepted.json() == {'tag': ['one', 'two']}
    assert rejected.status_code == 422
    assert rejected.json()['errors'][0]['loc'] == ['query', 'tag']
    assert rejected.json()['errors'][0]['type'] == 'duplicate_parameter'
