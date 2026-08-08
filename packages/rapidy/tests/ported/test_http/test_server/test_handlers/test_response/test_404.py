from http import HTTPStatus

from rapidy import Rapidy
from rapidy.http import controller, get
from rapidy.typedefs import View
from tests.ported.client import AppClientFactory


async def test_func_handler_404(app_client: AppClientFactory) -> None:
    async def handler() -> str:
        return ''

    rapidy = Rapidy(http_route_handlers=[get.reg('/', handler)])
    await _test(app_client, rapidy)


async def test_class_handler_404(app_client: AppClientFactory) -> None:
    class ViewHandler(View):
        async def get(self) -> str:
            return ''

    rapidy = Rapidy(http_route_handlers=[controller.reg('/', ViewHandler)])
    await _test(app_client, rapidy)


async def test_controller_404(app_client: AppClientFactory) -> None:
    @controller('/')
    class ControllerHandler:
        @get()
        async def get(self) -> str:
            return ''

    rapidy = Rapidy(http_route_handlers=[ControllerHandler])
    await _test(app_client, rapidy)


async def _test(app_client: AppClientFactory, rapidy: Rapidy) -> None:
    client = await app_client(rapidy)
    resp = await client.get('/wrong')

    assert resp.status == HTTPStatus.NOT_FOUND
