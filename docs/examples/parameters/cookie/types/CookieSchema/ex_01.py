from pydantic import BaseModel, Field
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import CookieSchema

routes = web.RouteTableDef()

class CookiesRequestSchema(BaseModel):
    user_id: str = Field(alias='userId')
    user_session: str = Field(alias='userSession')

@routes.get('/')
async def handler(
        request: web.Request,
        cookies: Annotated[CookiesRequestSchema, CookieSchema],
) -> web.Response:
    return web.json_response({'user_id': cookies.user_id, 'user_session': cookies.user_session})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)