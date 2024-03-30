from rapidy import web
from rapidy.typedefs import HandlerType

@web.middleware
async def hello_middleware(
        request: web.Request,
        handler: HandlerType,
) -> web.StreamResponse:
    request['data'] = {'hello': 'rapidy'}
    return await handler(request)

async def handler(request: web.Request) -> dict[str, str]:
    return request['data']

app = web.Application(middlewares=[hello_middleware])
app.add_routes([web.get('/', handler)])
