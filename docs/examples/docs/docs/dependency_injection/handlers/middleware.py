from rapidy import Rapidy
from rapidy.http import Request, StreamResponse, get, middleware
from rapidy.typedefs import CallNext
from rapidy.depends import FromDI
from .providers import FooProvider

@middleware
async def some_middleware(
    request: Request,
    call_next: CallNext,
    c: FromDI[int],
) -> StreamResponse:
    print({"value": c})
    return await call_next(request)

@get('/')
async def handler(c: FromDI[int]) -> dict:
    return {"value": c}

app = Rapidy(
    middlewares=[some_middleware],
    http_route_handlers=[handler],
    di_providers=[FooProvider()],
)