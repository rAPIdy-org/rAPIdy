from rapidy import Rapidy
from rapidy.http import middleware, get, Request, StreamResponse
from rapidy.typedefs import CallNext

@middleware
async def hello_rapidy_middleware(request: Request, call_next: CallNext) -> StreamResponse:
    print('before')
    handler_response = await call_next(request)
    print('after')
    return handler_response

@get('/')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy(
    http_route_handlers=[handler],
    middlewares=[hello_rapidy_middleware],
)