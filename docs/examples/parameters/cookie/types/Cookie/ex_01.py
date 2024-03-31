from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import Cookie

routes = web.RouteTableDef()

@routes.get('/')
async def handler(
        request: web.Request,
        user_id: Annotated[str, Cookie(alias='UserId')],
        user_session: Annotated[str, Cookie(alias='UserSession')],
) -> web.Response:
    return web.json_response({'user_id': user_id, 'user_session': user_session})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
