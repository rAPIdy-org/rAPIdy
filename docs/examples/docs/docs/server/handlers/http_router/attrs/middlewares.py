from rapidy.http import middleware, Request, StreamResponse, HTTPRouter
from rapidy.typedefs import CallNext

@middleware
async def hello_middleware(request: Request, call_next: CallNext) -> StreamResponse:
    print('hello')
    return await call_next(request)

router = HTTPRouter(
    path='/api',
    middlewares=[hello_middleware],
)