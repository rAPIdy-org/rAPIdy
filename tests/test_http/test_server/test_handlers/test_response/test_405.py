from http import HTTPStatus
from typing import Final

from aiohttp.pytest_plugin import AiohttpClient

from rapidy import Rapidy, web
from rapidy.http import controller, get
from rapidy.web import View

PATH: Final[str] = '/'


async def test_func(aiohttp_client: AiohttpClient) -> None:
    async def handler() -> str:
        return ''

    rapidy = Rapidy()
    rapidy.add_routes([web.get(PATH, handler)])
    await _test(aiohttp_client, rapidy)


async def test_vi(aiohttp_client: AiohttpClient) -> None:
    class ViewHandler(View):
        async def get(self) -> str:
            return ''

    rapidy = Rapidy()
    rapidy.add_routes([web.get(PATH, ViewHandler)])
    await _test(aiohttp_client, rapidy)


async def test_controller(aiohttp_client: AiohttpClient) -> None:
    @controller(PATH)
    class ControllerHandler:
        @get()
        async def get(self) -> str:
            return ''

    rapidy = Rapidy(http_route_handlers=[ControllerHandler])
    await _test(aiohttp_client, rapidy)


async def _test(aiohttp_client: AiohttpClient, rapidy: Rapidy) -> None:
    client = await aiohttp_client(rapidy)
    resp = await client.post(PATH)

    assert resp.status == HTTPStatus.METHOD_NOT_ALLOWED
