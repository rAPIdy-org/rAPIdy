from rapidy import Rapidy
from rapidy.http import delete, get


@delete('/no-content', status_code=204)
async def no_content() -> str:
    return 'ignored'


@get('/server')
async def server() -> str:
    return 'ok'


app = Rapidy(
    server_info_in_response=True,
    http_route_handlers=[no_content, server],
)


@get('/server')
async def default_server() -> str:
    return 'ok'


default_app = Rapidy(http_route_handlers=[default_server])
