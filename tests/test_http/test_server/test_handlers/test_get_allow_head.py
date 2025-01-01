from typing import Callable

import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import Rapidy, web
from rapidy.routing.http.routers import get


async def handler() -> None:
    pass


def create_app_routing_handler_use_deco(allow_head: bool) -> Rapidy:
    return Rapidy(http_route_handlers=[get('/', allow_head=allow_head)(handler)])


def create_app_routing_handler_use_cls_method(allow_head: bool) -> Rapidy:
    return Rapidy(http_route_handlers=[get.handler('/', handler, allow_head=allow_head)])


def create_app_web_method(allow_head: bool) -> Rapidy:
    app = Rapidy()
    app.router.add_get('/', handler, allow_head=allow_head)
    return app


def create_app_use_router_add_method(allow_head: bool) -> Rapidy:
    app = Rapidy()
    app.add_routes([web.get('/', handler, allow_head=allow_head)])
    return app


def create_app_use_router_table_def(allow_head: bool) -> Rapidy:
    route_table_def = web.RouteTableDef()
    route_table_def.get('/', allow_head=allow_head)(handler)
    app = Rapidy()
    app.add_routes(route_table_def)
    return app


@pytest.mark.parametrize(
    'app_factory',
    [
        create_app_routing_handler_use_deco,
        create_app_routing_handler_use_cls_method,
        create_app_web_method,
        create_app_use_router_add_method,
        create_app_use_router_table_def,
    ],
)
@pytest.mark.parametrize('allow_head', [True, False])
async def test_allow_head(
    aiohttp_client: AiohttpClient,
    app_factory: Callable[[bool], Rapidy],
    allow_head: bool,
) -> None:
    rapidy = app_factory(allow_head)

    client = await aiohttp_client(rapidy)

    resp = await client.get('/')
    assert resp.status == 200

    resp = await client.head('/')
    assert resp.status == 200 if allow_head else 405
