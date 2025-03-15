from rapidy import web
from rapidy.http import HTTPRouter, get
from pydantic import BaseModel

routes = web.RouteTableDef()

class UserData(BaseModel):
    name: str
    age: int

@routes.get('/user')
async def get_user_aiohttp(request: web.Request) -> web.Response:
    # ... some aiohttp code
    return web.Response(text='User aiohttp')

v1_app = web.Application()
v1_app.add_routes(routes)

# --- new functionality
@get('/user')
async def get_user_rapidy() -> str:
    return 'User rapidy'

v2_router = HTTPRouter('/v2', route_handlers=[get_user_rapidy])
# ---

app = web.Application(http_route_handlers=[v2_router])
app.add_subapp('/v1', v1_app)
