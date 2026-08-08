from http import HTTPStatus
from typing import TypeVar

import pytest

from rapidy import Rapidy
from rapidy.http import controller, get, middleware, Request, Response
from rapidy.typedefs import CallNext, Handler, HandlerOrView, View
from tests.ported.client import AppClientFactory

THandler = TypeVar('THandler')


def add_some_attr_deco(handler: THandler) -> THandler:  # noqa: UP047 - parity with the 1.x test helper
    handler.__some_attr__ = True  # type: ignore[attr-defined]
    return handler


def some_attr_exist(handler: Handler) -> bool:
    return getattr(handler, '__some_attr__', False)


@add_some_attr_deco
async def handler() -> None:
    pass


@add_some_attr_deco
class ViewHandler(View):
    async def get(self) -> None:
        pass


@pytest.mark.parametrize('handler', [handler, ViewHandler])
async def test_success_handler_add_attr(app_client: AppClientFactory, handler: HandlerOrView) -> None:
    @middleware
    async def some_attr_middleware(request: Request, call_next: CallNext) -> Response:
        assert some_attr_exist(handler)
        return await call_next(request)

    route = controller.reg('/', handler) if isinstance(handler, type) else get.reg('/', handler)
    app = Rapidy(middlewares=[some_attr_middleware], http_route_handlers=[route])

    client = await app_client(app)
    resp = await client.get('/')

    assert resp.status == HTTPStatus.OK
