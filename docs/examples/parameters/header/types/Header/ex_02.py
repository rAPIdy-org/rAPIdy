from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import Path

routes = web.RouteTableDef()

@routes.get('/{user_id}/{some_param}')
async def handler(
    request: web.Request,
    user_id: Annotated[str, Path],
    some_param: Annotated[str, Path],
) -> web.Response:
    return web.json_response({'user_id': user_id, 'some_param': some_param})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
