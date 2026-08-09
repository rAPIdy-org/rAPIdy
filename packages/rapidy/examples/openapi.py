from __future__ import annotations

import os
from typing import Annotated

from pydantic import BaseModel, Field

from rapidy import Rapidy, run_app
from rapidy.http import Body, get, PathParam, post, QueryParam
from rapidy.openapi import OpenAPIComponents, OpenAPIConfig, RedocRenderPlugin, SwaggerRenderPlugin
from rapidy.security import BearerAuth, constant_time_compare, SecurityConfig, SimpleUser


class ItemIn(BaseModel):
    """Validated item payload."""

    name: str = Field(min_length=1, description='Human-readable item name')


class ItemOut(ItemIn):
    """Item returned by the API."""

    id: int


@get(
    '/items/{item_id:\\d+}',
    tags=['items'],
    operation_id='readItem',
    summary='Read an item',
    responses={404: {'$ref': '#/components/responses/NotFound'}},
    security=[],
)
async def read_item(item_id: int = PathParam()) -> ItemOut:
    """Return one public item by its integer identifier."""
    return ItemOut(id=item_id, name='Example')


@post(
    '/items',
    status_code=201,
    tags=['items'],
    operation_id='createItem',
    response_links={
        'item': {
            'operationId': 'readItem',
            'parameters': {'item_id': '$response.body#/id'},
        },
    },
)
async def create_item(
    payload: Annotated[ItemIn, Body(description='Item to create')],
    notify: Annotated[bool, QueryParam(default=False)],
) -> ItemOut:
    """Create a validated item."""
    del notify
    return ItemOut(id=1, **payload.model_dump())


async def verify_token(token: str) -> SimpleUser | None:
    """Stand in for application-owned JWT verification."""
    expected = os.environ.get('ITEMS_BEARER_TOKEN')
    if expected is None or not constant_time_compare(token, expected):
        return None
    return SimpleUser('example-client')


security = SecurityConfig(
    schemes=[BearerAuth(verify_token, bearer_format='JWT')],
    requirements=[{'bearerAuth': []}],
)


app = Rapidy(
    http_route_handlers=[read_item, create_item],
    security=security,
    openapi_config=OpenAPIConfig(
        title='Items API',
        version='1.0.0',
        description='A small OpenAPI-enabled rAPIdy application.',
        tags=({'name': 'items', 'description': 'Item operations'},),
        components=OpenAPIComponents(
            responses={'NotFound': {'description': 'Item not found'}},
        ),
        security=({'bearerAuth': ()},),
        render_plugins=(
            SwaggerRenderPlugin(options={'displayRequestDuration': True}),
            RedocRenderPlugin(),
        ),
    ),
)


if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000)
