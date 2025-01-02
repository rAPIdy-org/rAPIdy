from rapidy import Rapidy
from rapidy.http import post, PathParam, Header, Body

from pydantic import BaseModel, Field

class BodyRequestSchema(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=40)

@post('/{user_id}')
async def handler(
        user_id: str = PathParam(),
        host: str = Header(alias='Host'),
        body: BodyRequestSchema = Body(),
) -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy(
    http_route_handlers=[handler],
)