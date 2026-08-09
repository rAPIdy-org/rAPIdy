from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, computed_field, Field, Json
from rapidy_core.enums import ContentType

from rapidy import Rapidy
from rapidy.http import Body, controller, Cookie, get, head, Header, PathParam, post, QueryParam, QueryParams
from rapidy.openapi import create_openapi_schema, OpenAPIConfig, OpenAPIGenerationError


class ItemIn(BaseModel):
    name: str = Field(description='Public item name')


class ItemOut(ItemIn):
    item_id: int


class QueryFilters(BaseModel):
    search: str
    page_size: int = Field(default=20, alias='limit', ge=1, le=100)


class RoundTripModel(BaseModel):
    raw: Json[list[int]]

    @computed_field
    @property
    def total(self) -> int:
        return sum(self.raw)


def test_openapi_schema_covers_operations_parameters_body_responses_and_components() -> None:
    @post(
        '/items/{item_id:\\d{1,8}}',
        status_code=201,
        operation_id='createItem',
        summary='Create an item',
        description='Create one item from a validated payload.',
        tags=['items'],
        deprecated=True,
        responses={404: {'description': 'Item not found'}},
    )
    async def create_item(
        item_id: int = PathParam(description='Internal identifier'),
        item: ItemIn = Body(description='Item payload'),
        page: int = QueryParam(default=1, ge=1),
        token: str = Header(alias='x-token'),
        session: str = Cookie(default='anonymous'),
    ) -> ItemOut:
        return ItemOut(item_id=item_id, name=item.name)

    app = Rapidy(http_route_handlers=[create_item])
    schema = create_openapi_schema(
        app.routes,
        OpenAPIConfig(
            title='Inventory',
            version='2026.1',
            description='Inventory API',
            servers=({'url': 'https://api.example.test'},),
            tags=({'name': 'items', 'description': 'Inventory operations'},),
        ),
    )

    assert schema['openapi'] == '3.1.0'
    assert schema['info'] == {
        'title': 'Inventory',
        'version': '2026.1',
        'description': 'Inventory API',
    }
    assert schema['servers'] == [{'url': 'https://api.example.test'}]
    assert schema['tags'] == [{'name': 'items', 'description': 'Inventory operations'}]

    operation = schema['paths']['/items/{item_id}']['post']
    assert operation['operationId'] == 'createItem'
    assert operation['summary'] == 'Create an item'
    assert operation['description'] == 'Create one item from a validated payload.'
    assert operation['tags'] == ['items']
    assert operation['deprecated'] is True
    assert operation['requestBody'] == {
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/ItemIn'},
            },
        },
        'description': 'Item payload',
        'required': True,
    }

    parameters = {(parameter['in'], parameter['name']): parameter for parameter in operation['parameters']}
    assert parameters[('path', 'item_id')]['required'] is True
    assert parameters[('path', 'item_id')]['schema'] == {'type': 'integer'}
    assert parameters[('path', 'item_id')]['description'] == 'Internal identifier'
    assert parameters[('query', 'page')]['schema'] == {'default': 1, 'minimum': 1, 'type': 'integer'}
    assert parameters[('header', 'x-token')]['required'] is True
    assert parameters[('cookie', 'session')]['required'] is False

    assert operation['responses']['201']['content']['application/json']['schema'] == {
        '$ref': '#/components/schemas/ItemOut',
    }
    assert operation['responses']['404'] == {'description': 'Item not found'}
    assert operation['responses']['422']['content']['application/json']['schema'] == {
        '$ref': '#/components/schemas/RapidyHTTPValidationError',
    }
    assert schema['components']['schemas'].keys() >= {
        'ItemIn',
        'ItemOut',
        'RapidyHTTPValidationError',
        'RapidyValidationError',
    }


def test_auto_head_and_hidden_routes_are_omitted_but_explicit_head_is_documented() -> None:
    @get('/visible')
    async def visible() -> str:
        return 'visible'

    @get('/hidden', include_in_schema=False)
    async def hidden() -> str:
        return 'hidden'

    @head('/health')
    async def health() -> None:
        return None

    schema = create_openapi_schema(Rapidy(http_route_handlers=[visible, hidden, health]).routes)

    assert schema['paths'].keys() == {'/visible', '/health'}
    assert schema['paths']['/visible'].keys() == {'get'}
    assert schema['paths']['/health'].keys() == {'head'}
    assert 'content' not in schema['paths']['/health']['head']['responses']['200']


def test_security_schemes_global_security_and_operation_overrides_are_documented() -> None:
    @get('/inherited')
    async def inherited() -> str:
        return 'protected by the document default'

    @get('/public', security=[])
    async def public() -> str:
        return 'public'

    @post('/scoped', security=[{'oauth': ['items:write']}])
    async def scoped() -> str:
        return 'scoped'

    @get('/optional', security=[{}])
    async def optional() -> str:
        return 'optional'

    config = OpenAPIConfig(
        security_schemes={
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
            'oauth': {
                'type': 'oauth2',
                'flows': {
                    'clientCredentials': {
                        'tokenUrl': 'https://auth.example.test/token',
                        'scopes': {'items:write': 'Create items'},
                    },
                },
            },
        },
        security=({'bearerAuth': ()},),
    )

    schema = create_openapi_schema(
        Rapidy(http_route_handlers=[inherited, public, scoped, optional]).routes,
        config,
    )

    assert schema['components']['securitySchemes'] == config.security_schemes
    assert schema['security'] == [{'bearerAuth': []}]
    assert 'security' not in schema['paths']['/inherited']['get']
    assert schema['paths']['/public']['get']['security'] == []
    assert schema['paths']['/scoped']['post']['security'] == [{'oauth': ['items:write']}]
    assert schema['paths']['/optional']['get']['security'] == [{}]


def test_invalid_security_metadata_is_rejected_during_schema_generation() -> None:
    @get('/protected', security=[{'missing': []}])
    async def protected() -> str:
        return 'protected'

    with pytest.raises(OpenAPIGenerationError, match="Unknown OpenAPI security scheme 'missing'"):
        create_openapi_schema(Rapidy(http_route_handlers=[protected]).routes)

    with pytest.raises(OpenAPIGenerationError, match='requires a non-empty `scheme`'):
        create_openapi_schema(
            (),
            OpenAPIConfig(security_schemes={'bearerAuth': {'type': 'http'}}),
        )


def test_controller_security_is_inherited_and_can_be_removed_by_a_child_route() -> None:
    @controller('/admin', security=[{'apiKey': []}])
    class AdminController:
        @get('/protected')
        async def protected(self) -> str:
            return 'protected'

        @get('/public', security=[])
        async def public(self) -> str:
            return 'public'

    schema = create_openapi_schema(
        Rapidy(http_route_handlers=[AdminController]).routes,
        OpenAPIConfig(
            security_schemes={
                'apiKey': {
                    'type': 'apiKey',
                    'name': 'X-API-Key',
                    'in': 'header',
                },
            },
        ),
    )

    assert schema['paths']['/admin/protected']['get']['security'] == [{'apiKey': []}]
    assert schema['paths']['/admin/public']['get']['security'] == []


def test_plural_query_model_expands_into_individual_openapi_parameters() -> None:
    @get('/search')
    async def search(filters: QueryFilters = QueryParams()) -> list[ItemOut]:
        return []

    schema = create_openapi_schema(Rapidy(http_route_handlers=[search]).routes)
    parameters = schema['paths']['/search']['get']['parameters']

    assert [(parameter['name'], parameter['required']) for parameter in parameters] == [
        ('search', True),
        ('limit', False),
    ]
    assert parameters[1]['schema'] == {
        'default': 20,
        'maximum': 100,
        'minimum': 1,
        'title': 'Limit',
        'type': 'integer',
    }


def test_mounted_routes_use_full_paths_in_root_schema() -> None:
    @get('/items/{item_id}')
    async def child_handler(item_id: int = PathParam()) -> ItemOut:
        return ItemOut(item_id=item_id, name='mounted')

    child = Rapidy(http_route_handlers=[child_handler])
    root = Rapidy(openapi_config=OpenAPIConfig(title='Root', version='1'))
    root.add_subapp('/v1', child)

    schema = root.openapi_schema
    assert schema is not None
    assert '/v1/items/{item_id}' in schema['paths']


@pytest.mark.asyncio
async def test_openapi_json_swagger_and_redoc_routes_are_served_and_not_self_documented() -> None:
    @get('/ping')
    async def ping() -> str:
        return 'pong'

    app = Rapidy(
        http_route_handlers=[ping],
        openapi_config=OpenAPIConfig(title='Example', version='1.0'),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        schema_response = await client.get('/schema/openapi.json')
        swagger_response = await client.get('/schema')
        redoc_response = await client.get('/schema/redoc')

    assert schema_response.status_code == 200
    assert schema_response.headers['content-type'].startswith('application/json')
    assert schema_response.json()['paths'].keys() == {'/ping'}
    assert swagger_response.status_code == 200
    assert swagger_response.headers['content-type'].startswith('text/html')
    assert 'SwaggerUIBundle' in swagger_response.text
    assert '"/schema/openapi.json"' in swagger_response.text
    assert redoc_response.status_code == 200
    assert redoc_response.headers['content-type'].startswith('text/html')
    assert 'spec-url="/schema/openapi.json"' in redoc_response.text


def test_schema_cache_is_invalidated_by_late_route_registration() -> None:
    app = Rapidy(openapi_config=OpenAPIConfig())
    first_schema = app.openapi_schema
    assert first_schema is not None
    assert first_schema['paths'] == {}

    @get('/late')
    async def late() -> dict[str, Any]:
        return {}

    app.add_http_router(late)
    second_schema = app.openapi_schema

    assert second_schema is not first_schema
    assert second_schema is not None
    assert '/late' in second_schema['paths']


def test_openapi_is_opt_in_and_config_rejects_ambiguous_paths() -> None:
    app = Rapidy()
    assert app.openapi_config is None
    assert app.openapi_schema is None
    assert app.routes == ()

    with pytest.raises(ValueError, match='must be unique'):
        OpenAPIConfig(json_path='/schema', swagger_path='/schema')
    with pytest.raises(ValueError, match='must start'):
        OpenAPIConfig(json_path='schema.json')


def test_duplicate_operation_ids_are_rejected() -> None:
    @get('/a', operation_id='duplicate')
    async def handler_a() -> str:
        return 'a'

    @post('/b', operation_id='duplicate')
    async def handler_b() -> str:
        return 'b'

    with pytest.raises(OpenAPIGenerationError, match='Duplicate OpenAPI operationId'):
        create_openapi_schema(Rapidy(http_route_handlers=[handler_a, handler_b]).routes)


def test_body_media_type_and_response_type_override_are_respected() -> None:
    @post(
        '/raw',
        response_type=bytes,
        response_content_type=ContentType.stream,
    )
    async def raw(payload: bytes = Body(content_type=ContentType.stream)) -> str:
        return payload.decode()

    operation = create_openapi_schema(Rapidy(http_route_handlers=[raw]).routes)['paths']['/raw']['post']

    assert operation['requestBody']['content']['application/octet-stream']['schema'] == {
        'format': 'binary',
        'type': 'string',
    }
    assert operation['responses']['200']['content']['application/octet-stream']['schema'] == {
        'format': 'binary',
        'type': 'string',
    }


def test_request_and_response_components_use_validation_and_serialization_modes() -> None:
    @post('/round-trip')
    async def round_trip(payload: RoundTripModel = Body()) -> RoundTripModel:
        return payload

    schema = create_openapi_schema(Rapidy(http_route_handlers=[round_trip]).routes)
    operation = schema['paths']['/round-trip']['post']
    request_reference = operation['requestBody']['content']['application/json']['schema']['$ref']
    response_reference = operation['responses']['200']['content']['application/json']['schema']['$ref']

    assert request_reference != response_reference
    request_schema = schema['components']['schemas'][request_reference.rsplit('/', 1)[-1]]
    response_schema = schema['components']['schemas'][response_reference.rsplit('/', 1)[-1]]
    assert request_schema['properties']['raw']['type'] == 'string'
    assert response_schema['properties']['raw']['type'] == 'array'
    assert response_schema['properties']['total']['readOnly'] is True
