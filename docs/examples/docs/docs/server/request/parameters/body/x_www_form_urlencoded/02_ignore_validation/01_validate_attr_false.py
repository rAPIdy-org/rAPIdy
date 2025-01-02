from pydantic import BaseModel
from rapidy.http import post, Body, ContentType

class BodyData(BaseModel):
    ...

@post('/')
async def handler(
    data: BodyData = Body(validate=False, content_type=ContentType.x_www_form),
) -> ...: