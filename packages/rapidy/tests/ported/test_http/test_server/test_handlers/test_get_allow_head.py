from typing import Callable

import pytest

from rapidy import Rapidy
from rapidy.routing.http.routers import get
from tests.ported.client import AppClientFactory


async def handler() -> None:
    pass


def create_app_routing_handler_use_deco(allow_head: bool) -> Rapidy:
    return Rapidy(http_route_handlers=[get('/', allow_head=allow_head)(handler)])


def create_app_routing_handler_use_cls_method(allow_head: bool) -> Rapidy:
    return Rapidy(http_route_handlers=[get.reg('/', handler, allow_head=allow_head)])


def create_app_add_http_router(allow_head: bool) -> Rapidy:
    app = Rapidy()
    app.add_http_router(get.reg('/', handler, allow_head=allow_head))
    return app


@pytest.mark.parametrize(
    'app_factory',
    [
        create_app_routing_handler_use_deco,
        create_app_routing_handler_use_cls_method,
        create_app_add_http_router,
    ],
)
@pytest.mark.parametrize('allow_head', [True, False])
async def test_allow_head(
    app_client: AppClientFactory,
    app_factory: Callable[[bool], Rapidy],
    allow_head: bool,
) -> None:
    rapidy = app_factory(allow_head)

    client = await app_client(rapidy)

    resp = await client.get('/')
    assert resp.status == 200

    resp = await client.head('/')
    assert resp.status == 200 if allow_head else 405
