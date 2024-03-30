from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import Header

routes = web.RouteTableDef()

@routes.get('/')
async def handler(
        request: web.Request,
        host: Annotated[str, Header(alias='Host')],
        auth_token: Annotated[str, Header(alias='Authorization')],
) -> web.Response:
    return web.json_response({'host': host, 'auth_token': auth_token})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
