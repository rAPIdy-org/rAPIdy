from rapidy import Rapidy  # <-- rapidy.Rapidy == rapidy.web.Application
from rapidy.http import get, HTTPRouter

@get('/get_hello')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

v1_app = HTTPRouter('/v1', route_handlers=[handler])
rapidy = Rapidy(http_route_handlers=[v1_app])