from rapidy import Rapidy
from rapidy.http import controller, get, HTTPRouter

@get('/hello')
async def hello_handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

@controller('/hello_controller')
class HelloController:
    @get()
    async def get(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

@get('/hi')
async def hi_handler() -> dict[str, str]:
    return {'hi': 'rapidy'}

@controller('/hi_controller')
class HiController:
    @get()
    async def get(self) -> dict[str, str]:
        return {'hi': 'rapidy'}

hello_api_router = HTTPRouter('/hello_api', [hello_handler, HelloController])

rapidy = Rapidy(
    http_route_handlers=[
        hello_api_router,
        hi_handler,
        HiController,
    ]
)
