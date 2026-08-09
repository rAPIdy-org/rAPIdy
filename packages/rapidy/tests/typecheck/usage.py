from __future__ import annotations

from pathlib import Path
from typing import Annotated, TYPE_CHECKING

from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.background import BackgroundTask, BackgroundTasks
from rapidy.depends import FromDI
from rapidy.http import Body, controller, get, PathParam, post, Response
from rapidy.middlewares import (
    CompressionMiddleware,
    CORSMiddleware,
    get_request_context,
    GZipMiddleware,
    HTTPSRedirectMiddleware,
    ProxyHeadersMiddleware,
    RequestContext,
    RequestIDMiddleware,
    TrustedHostMiddleware,
)
from rapidy.openapi import create_openapi_schema, OpenAPIComponents, OpenAPIConfig, SwaggerRenderPlugin
from rapidy.responses import FileResponse
from rapidy.security import APIKeyAuth, AuthCredentials, SecurityConfig, SecurityIdentity
from rapidy.staticfiles import StaticFiles
from rapidy.testing import (
    AsyncSSESession,
    AsyncTestClient,
    AsyncWebSocketSession,
    create_test_client,
    TestClient,
)


class Payload(BaseModel):
    value: int


async def notify(value: int) -> None:
    value.bit_length()


background_task: BackgroundTask = BackgroundTask(notify, 20)
background_tasks = BackgroundTasks([background_task])
background_tasks.add_task(notify, 21)
typed_response: Response = Response('accepted', background=background_tasks)
file_response: FileResponse = FileResponse(Path('report.txt'), filename='report.txt', background=background_task)
static_files: StaticFiles = StaticFiles('/assets', directory=Path())


@get('/items/{item_id}')
async def get_item(item_id: Annotated[int, PathParam()]) -> dict[str, int]:
    return {'item_id': item_id}


@post('/items')
async def create_item(payload: Annotated[Payload, Body()], dependency: FromDI[str]) -> Payload:
    dependency.upper()
    return payload


@controller('/typed-controller')
class TypedController:
    @get('/item')
    async def item(self) -> dict[str, bool]:
        return {'typed': True}


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
security_config = SecurityConfig(
    schemes=[APIKeyAuth(key='typed-key')],
    requirements=[{'apiKey': []}],
)
app: Rapidy = Rapidy(
    http_route_handlers=[get_item, create_item, TypedController],
    middlewares=[
        ProxyHeadersMiddleware(['127.0.0.1']),
        TrustedHostMiddleware(['example.com']),
        HTTPSRedirectMiddleware(['example.com']),
        RequestIDMiddleware(),
        CORSMiddleware(allow_origins=['https://example.com']),
        CompressionMiddleware(algorithms=['gzip']),
        GZipMiddleware(),
    ],
    openapi_config=openapi_config,
    security=security_config,
)
openapi_schema: dict[str, object] | None = app.openapi_schema
generated_schema: dict[str, object] = create_openapi_schema(app.routes, openapi_config)
sync_client: TestClient = create_test_client([get_item])
async_client: AsyncTestClient = AsyncTestClient(app)

if TYPE_CHECKING:
    request_context: RequestContext | None = get_request_context()
    security_identity: SecurityIdentity
    auth_credentials: AuthCredentials
    websocket_session: AsyncWebSocketSession = async_client.websocket_connect('/ws')
    sse_session: AsyncSSESession = async_client.sse_connect('/events')
