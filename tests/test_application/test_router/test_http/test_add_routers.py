from typing import Any, Callable

import pytest
from pytest_aiohttp.plugin import AiohttpClient

from rapidy import http as http_route_module, Rapidy
from rapidy.http import get
from rapidy.routing.http.routers import HTTPRouteHandler, HTTPRouter, IncorrectHandlerTypeError
from tests.test_application.test_router.test_http.helpers import parametrize_method_names, PATH_1, PATH_2


async def handler() -> None: pass


def create_routing_handler(method_name: str, path: str) -> HTTPRouteHandler:
    """
    from rapidy import web
    from rapidy.routing.http import get

    @get('/foo')
    def handler -> None: pass

    HTTPRouter(
        route_handlers = [
            handler,
        ],
    )
    """
    return getattr(http_route_module, method_name)(path)(handler)


def create_routing_handler_using_cls_method(method_name: str, path: str) -> HTTPRouteHandler:
    """
    from rapidy import web
    from rapidy.routing.http import get

    def handler -> None: pass

    HTTPRouter(
        route_handlers = [
            get.handler('/foo', handler),
        ],
    )
    """
    return getattr(http_route_module, method_name).handler(path, handler)


handler_fabrics_parametrize = pytest.mark.parametrize(
    'handler_fabric',
    [
        pytest.param(create_routing_handler, id='decorator'),
        pytest.param(create_routing_handler_using_cls_method, id='cls-method'),
    ],
)


@handler_fabrics_parametrize
@parametrize_method_names
async def test_app_add_only_router(
        aiohttp_client: AiohttpClient,
        handler_fabric: Callable[[str, str], Any],
        method_name: str,
) -> None:
    app = Rapidy()

    handler_1 = handler_fabric(method_name, PATH_1)
    handler_2 = handler_fabric(method_name, PATH_2)

    api_router = HTTPRouter('/api', route_handlers=[handler_1, handler_2])

    app.add_http_route_handler(api_router)
    client = await aiohttp_client(app)

    client_method = getattr(client, method_name)

    resp = await client_method(f'/api{PATH_1}')
    assert resp.status == 200

    resp = await client_method(f'/api{PATH_2}')
    assert resp.status == 200


@handler_fabrics_parametrize
@parametrize_method_names
async def test_app_add_router_and_handler(
        aiohttp_client: AiohttpClient,
        handler_fabric: Callable[[str, str], Any],
        method_name: str,
) -> None:
    route_handler = handler_fabric(method_name, PATH_1)
    app_handler = handler_fabric(method_name, PATH_2)

    api_router = HTTPRouter(
        '/api',
        route_handlers=[route_handler],
    )

    app = Rapidy()
    app.add_http_route_handlers([api_router, app_handler])
    client = await aiohttp_client(app)

    client_method = getattr(client, method_name)

    resp = await client_method(f'/api{PATH_1}')
    assert resp.status == 200

    resp = await client_method(f'{PATH_2}')
    assert resp.status == 200


@handler_fabrics_parametrize
@parametrize_method_names
async def test_nested_router(
        aiohttp_client: AiohttpClient,
        handler_fabric: Callable[[str, str], Any],
        method_name: str,
) -> None:
    handler = handler_fabric(method_name, PATH_1)

    v1_router = HTTPRouter(
        '/v1',
        route_handlers=[handler],
    )

    api_router = HTTPRouter(
        '/api',
        route_handlers=[v1_router],
    )

    app = Rapidy()
    app.add_http_route_handlers([api_router])
    client = await aiohttp_client(app)

    client_method = getattr(client, method_name)

    resp = await client_method(f'/api/v1{PATH_1}')
    assert resp.status == 200


async def test_incorrect_route_handler(aiohttp_client: AiohttpClient) -> None:
    @get('/')  # type: ignore[arg-type]
    def wrong_handler() -> None: pass

    app = Rapidy()
    with pytest.raises(IncorrectHandlerTypeError):
        app.add_http_route_handlers([wrong_handler])
