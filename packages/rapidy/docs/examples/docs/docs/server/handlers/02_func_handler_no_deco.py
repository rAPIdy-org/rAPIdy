from rapidy import Rapidy
from rapidy.http import post

async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy(
    http_route_handlers=[
        post.reg('/', handler),
    ]
)
