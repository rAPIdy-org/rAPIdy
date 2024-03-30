from rapidy import web
from pydantic import BaseModel, Field

routes = web.RouteTableDef()

class BodyRequestSchema(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=40)

@routes.post('/api/{user_id}')
async def handler(
        user_id: str = web.PathParam(),
        host: str = web.Header(alias='Host'),
        body: BodyRequestSchema = web.Body(),
) -> dict[str, str]:
    return {'hello': 'rapidy'}

app = web.Application()
app.add_routes(routes)