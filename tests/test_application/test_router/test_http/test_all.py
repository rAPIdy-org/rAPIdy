import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web
from rapidy.routing.http import routers as http_route_module
from rapidy.routing.http.routers import HTTPRouter
from tests.test_application.test_router.test_http.helpers import parametrize_method_names, PATH_1, PATH_2


@pytest.mark.parametrize('path', [PATH_1, PATH_2, f'/api{PATH_1}', f'/api{PATH_2}'])
@parametrize_method_names
async def test_all(aiohttp_client: AiohttpClient, path: str, method_name: str) -> None:
    method_func = getattr(http_route_module, method_name)

    @method_func(PATH_1)
    async def app_handler1() -> None: pass
    async def app_handler2() -> None: pass

    @method_func(PATH_1)
    async def router_handler1() -> None: pass
    async def router_handler2() -> None: pass

    api_router = HTTPRouter(
        '/api',
        route_handlers=[
            router_handler1,
            method_func.handler(PATH_2, router_handler2),
        ],
    )

    app = web.Application(
        http_route_handlers=[
            api_router,  # add router
            app_handler1,
            method_func.handler(PATH_2, app_handler2),
        ],
    )
    client = await aiohttp_client(app)

    client_method = getattr(client, method_name)

    resp = await client_method(path)
    assert resp.status == 200
