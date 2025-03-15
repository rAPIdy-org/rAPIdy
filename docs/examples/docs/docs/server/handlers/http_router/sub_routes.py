from rapidy import Rapidy
from rapidy.http import HTTPRouter, get

@get('/hello')  # /api/v1/hello
async def hello_handler_v1() -> dict[str, str | int]:
    return {'hello': 'rapidy', 'version': 1}

@get('/hello')  # /api/v2/hello
async def hello_handler_v2() -> dict[str, str | int]:
    return {'hello': 'rapidy', 'version': 2}

v1_router = HTTPRouter('/v1', [hello_handler_v1])
v2_router = HTTPRouter('/v2', [hello_handler_v2])

api_router = HTTPRouter('/api', [v1_router, v2_router])

rapidy = Rapidy(http_route_handlers=[api_router])