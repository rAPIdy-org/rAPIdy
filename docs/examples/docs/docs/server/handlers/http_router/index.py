from rapidy import Rapidy
from rapidy.http import HTTPRouter, get

@get('/healthcheck')  # /healthcheck
async def healthcheck() -> str:
    return 'ok'

@get('/hello')  # /api/hello
async def hello_handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

api_router = HTTPRouter('/api', [hello_handler])

rapidy = Rapidy(http_route_handlers=[healthcheck, api_router])