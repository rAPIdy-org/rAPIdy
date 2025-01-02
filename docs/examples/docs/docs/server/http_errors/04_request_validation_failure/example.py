from pydantic import BaseModel, Field
from rapidy import Rapidy
from rapidy.http import post, Body

class BodyRequestSchema(BaseModel):
    data: str = Field(min_length=3, max_length=20)

@post('/')
async def handler(
        body: BodyRequestSchema = Body(),
) -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy(http_route_handlers=[handler])