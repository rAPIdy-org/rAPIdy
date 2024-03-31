from pydantic import BaseModel, Field
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import HeaderSchema

routes = web.RouteTableDef()

class HeadersRequestSchema(BaseModel):
    host: str = Field(alias='Host')
    auth_token: str = Field(alias='Authorization')

@routes.get('/')
async def handler(
        request: web.Request,
        headers: Annotated[HeadersRequestSchema, HeaderSchema],
) -> web.Response:
    return web.json_response({'host': headers.host, 'auth_token': headers.auth_token})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
