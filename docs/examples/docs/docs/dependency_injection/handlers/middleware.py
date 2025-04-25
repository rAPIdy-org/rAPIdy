from rapidy import Rapidy
from rapidy.http import Request, StreamResponse, get, middleware
from rapidy.typedefs import CallNext
from rapidy.depends import Depends
from .providers import FooProvider

@middleware
async def sample_middleware(request: Request, call_next: CallNext, c: Depends[int]) -> StreamResponse:
    print({"value": c})
    return await call_next(request)

@get('/')
async def handler(c: Depends[int]) -> dict:
    return {"value": c}

app = Rapidy(
    middlewares=[sample_middleware],
    http_route_handlers=[handler],
    di_providers=[FooProvider()],
)