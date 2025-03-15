from pydantic import BaseModel
from rapidy.http import post, Body, ContentType

class BodyData(BaseModel):
    ...

@post('/')
async def handler(
    data: BodyData = Body('some_data', content_type=ContentType.m_part_form_data),
    # or
    data: BodyData = Body(default_factory=lambda: 'some_data', content_type=ContentType.m_part_form_data),
) -> ...: