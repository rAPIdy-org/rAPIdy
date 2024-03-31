from typing import Dict
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import CookieRaw

routes = web.RouteTableDef()

@routes.get('/')
async def handler(
    request: web.Request,
    cookies: Annotated[Dict[str, str], CookieRaw],
) -> web.Response:
    return web.json_response({'cookies': cookies})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
