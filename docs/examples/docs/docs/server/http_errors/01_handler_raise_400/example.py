from rapidy import Rapidy
from rapidy.http import get, HTTPBadRequest

@get('/')
async def handler() -> None:
    raise HTTPBadRequest()  # 400

app = Rapidy(http_route_handlers=[handler])