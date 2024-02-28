from http import HTTPStatus

from pytest_aiohttp.plugin import AiohttpClient

from rapidy import web
from rapidy.typedefs import HandlerType
from rapidy.web import middleware


async def test_success(aiohttp_client: AiohttpClient) -> None:
    @middleware
    async def simple_middleware(request: web.Request, handler: HandlerType) -> web.StreamResponse:
        return await handler(request)

    async def handler(request: web.Request) -> web.Response:
        return web.Response()

    app = web.Application(middlewares=[simple_middleware])
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/', data='1')
    assert resp.status == HTTPStatus.OK
