from pydantic import BaseModel

from rapidy.http import post, Body, ContentType

class BodyData(BaseModel):
    ...

@post('/')
async def handler(
    data: BodyData | None = Body(content_type=ContentType.x_www_form),
    # or
    data: Optional[BodyData] = Body(content_type=ContentType.x_www_form),
    # or
    data: Union[BodyData, None] = Body(content_type=ContentType.x_www_form),
) -> ...: