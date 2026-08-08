from aiohttp import web
from pydantic import BaseModel, ValidationError

routes = web.RouteTableDef()

class UserData(BaseModel):
    name: str
    age: int

@routes.post('/user')
async def create_user(request: web.Request) -> web.Response:
    data = await request.json()
    try:
        user = UserData(**data)
    except ValidationError as validation_err:
        return web.json_response({'error': validation_err.errors()}, status=400)
    return web.json_response({'message': f'User {user.name}, {user.age} years old'})

async def on_startup(app: web.Application) -> None:
    print("App is starting...")

app = web.Application()
app.on_startup.append(on_startup)
app.add_routes(routes)

web.run_app(app)