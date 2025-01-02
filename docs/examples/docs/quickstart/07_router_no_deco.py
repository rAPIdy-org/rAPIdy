from rapidy import Rapidy
from rapidy.http import HTTPRouter, controller, get

async def hello_handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

class HelloController:
    @get()
    async def get_hello(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

api_router = HTTPRouter(
    '/api',
    [
        get.reg('/hello', hello_handler),
        controller.reg('/hello_controller', HelloController),
    ]
)

rapidy = Rapidy(http_route_handlers=[api_router])
