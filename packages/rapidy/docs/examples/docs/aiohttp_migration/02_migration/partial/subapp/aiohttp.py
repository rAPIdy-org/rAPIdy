from aiohttp import web
from pydantic import BaseModel

routes = web.RouteTableDef()

class UserData(BaseModel):
    name: str
    age: int

@routes.post('/user')
async def create_user(request: web.Request) -> web.Response:
    # ... some aiohttp code
    return web.Response(text='User')

v1_app = web.Application()
v1_app.add_routes(routes)

app = web.Application()
app.add_subapp('/v1', v1_app)

