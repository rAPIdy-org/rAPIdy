from typing import Dict
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import PathRaw

routes = web.RouteTableDef()

@routes.get('/{user_id}/{some_param}')
async def handler(
    request: web.Request,
    path: Annotated[Dict[str, str], PathRaw],
) -> web.Response:
    return web.json_response({'path': path})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
