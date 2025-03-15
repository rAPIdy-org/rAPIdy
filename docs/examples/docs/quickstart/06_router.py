from rapidy import Rapidy
from rapidy.http import HTTPRouter, controller, get

@get('/hello')
async def hello_handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

@controller('/hello_controller')
class HelloController:
    @get()
    async def get_hello(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

api_router = HTTPRouter('/api', [hello_handler, HelloController])

rapidy = Rapidy(http_route_handlers=[api_router])
