from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import Path

routes = web.RouteTableDef()

@routes.get('/get_user_info/{user_id}', name='user_info')
async def get_user_info_handler(
    request: web.Request,
    user_id: Annotated[str, Path],
) -> web.Response:
    return web.json_response({'user_id': user_id})

@routes.get('/')
async def handler(request: web.Request) -> web.Response:
    user_id = 'user_1'
    router = request.app.router['user_info']
    url = router.url_for(user_id=user_id)
    return web.Response(status=302, headers={"Location": str(url)})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)