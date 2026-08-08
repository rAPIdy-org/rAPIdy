from http import HTTPStatus

from aiohttp.pytest_plugin import AiohttpClient

from rapidy import Rapidy, web
from rapidy.http import controller, get


async def test_func_handler_404(aiohttp_client: AiohttpClient) -> None:
    async def handler() -> str:
        return ''

    rapidy = web.Application()
    rapidy.add_routes([web.get('/', handler)])
    await _test(aiohttp_client, rapidy)


async def test_class_handler_404(aiohttp_client: AiohttpClient) -> None:
    class ViewHandler(web.View):
        def get(self) -> str:
            return ''

    rapidy = Rapidy()
    rapidy.add_routes([web.view('/', ViewHandler)])
    await _test(aiohttp_client, rapidy)


async def test_controller_404(aiohttp_client: AiohttpClient) -> None:
    @controller('/')
    class ControllerHandler:
        @get()
        async def get(self) -> str:
            return ''

    rapidy = Rapidy(http_route_handlers=[ControllerHandler])
    await _test(aiohttp_client, rapidy)


async def _test(aiohttp_client: AiohttpClient, rapidy: Rapidy) -> None:
    client = await aiohttp_client(rapidy)
    resp = await client.get('/wrong')

    assert resp.status == HTTPStatus.NOT_FOUND
