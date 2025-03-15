from rapidy import Rapidy
from rapidy.http import get

@get('/')
async def handler() -> ...:
    ...

app = Rapidy(http_route_handlers=[handler])