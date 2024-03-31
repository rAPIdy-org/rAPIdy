from pydantic import BaseModel, Field
from typing_extensions import Annotated
from rapidy import web
from rapidy.request_params import QuerySchema

routes = web.RouteTableDef()

class QueryRequestSchema(BaseModel):
    user_id: str = Field(alias='userId')
    user_filter_value: str = Field(alias='userFilterValue')

@routes.get('/')
async def handler(
        request: web.Request,
        query_parameters: Annotated[QueryRequestSchema, QuerySchema],
) -> web.Response:
    return web.json_response({'user_id': query_parameters.user_id, 'user_session': query_parameters.user_filter_value})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
