from pydantic import BaseModel
from rapidy.http import post, Body

class BodyData(BaseModel):
    ...

@post('/')
async def handler(
    data: BodyData = Body(validate=False),
) -> ...: