from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from rapidy import Rapidy, run_app
from rapidy.http import Body, get, PathParam, post, QueryParam
from rapidy.openapi import OpenAPIConfig, RedocRenderPlugin, SwaggerRenderPlugin


class ItemIn(BaseModel):
    """Validated item payload."""

    name: str = Field(min_length=1, description='Human-readable item name')


class ItemOut(ItemIn):
    """Item returned by the API."""

    id: int


@get('/items/{item_id:\\d+}', tags=['items'], summary='Read an item', security=[])
async def read_item(item_id: int = PathParam()) -> ItemOut:
    """Return one public item by its integer identifier."""
    return ItemOut(id=item_id, name='Example')


@post('/items', status_code=201, tags=['items'], operation_id='createItem')
async def create_item(
    payload: Annotated[ItemIn, Body(description='Item to create')],
    notify: Annotated[bool, QueryParam(default=False)],
) -> ItemOut:
    """Create a validated item."""
    del notify
    return ItemOut(id=1, **payload.model_dump())


app = Rapidy(
    http_route_handlers=[read_item, create_item],
    openapi_config=OpenAPIConfig(
        title='Items API',
        version='1.0.0',
        description='A small OpenAPI-enabled rAPIdy application.',
        tags=({'name': 'items', 'description': 'Item operations'},),
        security_schemes={
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
        },
        security=({'bearerAuth': ()},),
        render_plugins=(
            SwaggerRenderPlugin(options={'displayRequestDuration': True}),
            RedocRenderPlugin(),
        ),
    ),
)


if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000)
