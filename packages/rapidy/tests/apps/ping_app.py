from rapidy import Rapidy
from rapidy.http import get


@get('/ping')
async def ping() -> str:
    return 'pong'


app = Rapidy(http_route_handlers=[ping])
