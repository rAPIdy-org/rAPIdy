from rapidy import Rapidy
from rapidy.http import get


@get('/')
async def handler() -> str:
    return 'ok'


rapidy = Rapidy(http_route_handlers=[handler])