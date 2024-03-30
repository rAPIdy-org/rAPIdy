from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import JsonBody

routes = web.RouteTableDef()

@routes.get('/')
async def handler(
    request: web.Request,
    username: Annotated[str, JsonBody(alias='awesomeUsername', min_length=1, max_length=10)],
    age: Annotated[int, JsonBody(gt=0)],
) -> web.Response:
    return web.json_response({'username': username, 'age': age})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
