from http import HTTPStatus
from typing import TypeVar

import pytest
from pytest_aiohttp.plugin import AiohttpClient

from rapidy import web
from rapidy.typedefs import CallNext, Handler, HandlerOrView

THandler = TypeVar('THandler')


def add_some_attr_deco(handler: THandler) -> THandler:
    handler.__some_attr__ = True  # type: ignore[attr-defined]
    return handler


def some_attr_exist(handler: Handler) -> bool:
    return getattr(handler, '__some_attr__', False)


@web.middleware
async def some_attr_middleware(request: web.Request, handler: CallNext) -> web.StreamResponse:
    true_handler = request.match_info.handler
    if some_attr_exist(true_handler):
        return await handler(request)

    raise web.HTTPInternalServerError


@add_some_attr_deco
async def handler() -> None:
    pass


@add_some_attr_deco
class ViewHandler(web.View):
    async def get(self) -> None:
        pass


@pytest.mark.parametrize('handler', [handler, ViewHandler])
async def test_success_handler_add_attr(aiohttp_client: AiohttpClient, handler: HandlerOrView) -> None:
    app = web.Application(middlewares=[some_attr_middleware])
    app.add_routes([web.get('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == HTTPStatus.OK
