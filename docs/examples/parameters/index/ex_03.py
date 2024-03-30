from pydantic import BaseModel, Field
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import JsonBodySchema

routes = web.RouteTableDef()

class UserData(BaseModel):
    username: str = Field(alias='awesomeUsername', min_length=1, max_length=10)
    age: int = Field(gt=0)

@routes.get('/')
async def handler(
    request: web.Request,
    userdata: Annotated[UserData, JsonBodySchema],
) -> web.Response:
    return web.json_response({'username': userdata.username, 'age': userdata.age})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
