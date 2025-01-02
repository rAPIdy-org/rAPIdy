from rapidy import Rapidy
from rapidy.http import get

@get('/hello')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy(http_route_handlers=[handler])