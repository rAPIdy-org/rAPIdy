from rapidy import Rapidy
from rapidy.http import get, HTTPRouter, middleware, Request, StreamResponse
from rapidy.typedefs import CallNext

@get('/hello')  # /api/v1/hello & /api/v2/hello
async def hello_handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

@middleware
async def auth_middleware_1(request: Request, call_next: CallNext) -> StreamResponse:
    # auth logic 1 ...
    print('auth 1 ...')
    return await call_next(request)

@middleware
async def auth_middleware_2(request: Request, call_next: CallNext) -> StreamResponse:
    # auth logic 2 ...
    print('auth 2 ...')
    return await call_next(request)

router_auth_1 = HTTPRouter('/v1', [hello_handler], middlewares=[auth_middleware_1])
router_auth_2 = HTTPRouter('/v2', [hello_handler], middlewares=[auth_middleware_2])

api_router = HTTPRouter('/api', [router_auth_1, router_auth_2])

rapidy = Rapidy(http_route_handlers=[api_router])