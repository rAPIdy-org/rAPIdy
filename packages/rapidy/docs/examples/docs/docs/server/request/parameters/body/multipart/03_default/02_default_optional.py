from pydantic import BaseModel
from rapidy.http import post, Body, ContentType

class BodyData(BaseModel):
    ...

@post('/')
async def handler(
    data: BodyData | None = Body(content_type=ContentType.m_part_form_data),
    # or
    data: Optional[BodyData] = Body(content_type=ContentType.m_part_form_data),
    # or
    data: Union[BodyData, None] = Body(content_type=ContentType.m_part_form_data),
) -> ...: