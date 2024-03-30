from pydantic import BaseModel
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import PathSchema

routes = web.RouteTableDef()

class PathRequestSchema(BaseModel):
    user_id: str

@routes.get('/{user_id}')
async def handler(
    request: web.Request,
    path: Annotated[PathRequestSchema, PathSchema],
) -> web.Response:
    return web.json_response({'user_id': path.user_id})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
