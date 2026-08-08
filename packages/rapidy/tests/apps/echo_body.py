from rapidy import Rapidy
from rapidy.http import get, Request


@get('/echo')
async def echo(request: Request) -> str:
    return await request.text()


app = Rapidy(http_route_handlers=[echo], client_max_size=10)
