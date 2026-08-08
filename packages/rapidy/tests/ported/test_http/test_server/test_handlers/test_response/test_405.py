from http import HTTPStatus
from typing import Final

from rapidy import Rapidy
from rapidy.http import controller, get
from rapidy.typedefs import View
from tests.ported.client import AppClientFactory

PATH: Final[str] = '/'


async def test_func(app_client: AppClientFactory) -> None:
    async def handler() -> str:
        return ''

    rapidy = Rapidy(http_route_handlers=[get.reg(PATH, handler)])
    await _test(app_client, rapidy)


async def test_vi(app_client: AppClientFactory) -> None:
    class ViewHandler(View):
        async def get(self) -> str:
            return ''

    rapidy = Rapidy(http_route_handlers=[controller.reg(PATH, ViewHandler)])
    await _test(app_client, rapidy)


async def test_controller(app_client: AppClientFactory) -> None:
    @controller(PATH)
    class ControllerHandler:
        @get()
        async def get(self) -> str:
            return ''

    rapidy = Rapidy(http_route_handlers=[ControllerHandler])
    await _test(app_client, rapidy)


async def _test(app_client: AppClientFactory, rapidy: Rapidy) -> None:
    client = await app_client(rapidy)
    resp = await client.post(PATH)

    assert resp.status == HTTPStatus.METHOD_NOT_ALLOWED
