from rapidy import Rapidy
from rapidy.http import post

@post('/')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.add_http_router(handler)
