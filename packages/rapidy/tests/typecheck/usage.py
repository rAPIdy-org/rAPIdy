from __future__ import annotations

from typing import Annotated, TYPE_CHECKING

from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.depends import FromDI
from rapidy.http import Body, get, PathParam, post
from rapidy.openapi import create_openapi_schema, OpenAPIComponents, OpenAPIConfig, SwaggerRenderPlugin
from rapidy.testing import (
    AsyncSSESession,
    AsyncTestClient,
    AsyncWebSocketSession,
    create_test_client,
    TestClient,
)


class Payload(BaseModel):
    value: int


@get('/items/{item_id}')
async def get_item(item_id: Annotated[int, PathParam()]) -> dict[str, int]:
    return {'item_id': item_id}


@post('/items')
async def create_item(payload: Annotated[Payload, Body()], dependency: FromDI[str]) -> Payload:
    dependency.upper()
    return payload


openapi_config = OpenAPIConfig(
    title='Typed API',
    version='1.0.0',
    components=OpenAPIComponents(
        responses={'NotFound': {'description': 'Item not found'}},
    ),
    render_plugins=(
        SwaggerRenderPlugin(
            js_url='/assets/swagger-ui-bundle.js',
            css_url='/assets/swagger-ui.css',
        ),
    ),
)
app: Rapidy = Rapidy(
    http_route_handlers=[get_item, create_item],
    openapi_config=openapi_config,
)
openapi_schema: dict[str, object] | None = app.openapi_schema
generated_schema: dict[str, object] = create_openapi_schema(app.routes, openapi_config)
sync_client: TestClient = create_test_client([get_item])
async_client: AsyncTestClient = AsyncTestClient(app)

if TYPE_CHECKING:
    websocket_session: AsyncWebSocketSession = async_client.websocket_connect('/ws')
    sse_session: AsyncSSESession = async_client.sse_connect('/events')
