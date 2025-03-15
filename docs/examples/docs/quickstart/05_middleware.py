from rapidy import Rapidy
from rapidy.http import Request, StreamResponse, get, middleware
from rapidy.typedefs import CallNext

@middleware
async def hello_middleware(request: Request, call_next: CallNext) -> StreamResponse:
    request['data'] = {'hello': 'rapidy'}
    return await call_next(request)

@get('/')
async def handler(request: Request) -> dict[str, str]:
    return request['data']

rapidy = Rapidy(
    http_route_handlers=[handler],
    middlewares=[hello_middleware],
)
