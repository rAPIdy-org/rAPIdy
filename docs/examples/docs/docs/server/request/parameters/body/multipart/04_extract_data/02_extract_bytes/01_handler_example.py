from rapidy.http import post, Body, ContentType

@post('/')
async def handler(
    user_data: bytes = Body(content_type=ContentType.m_part_form_data),
    # also you can use pydantic validation
    user_data: bytes = Body(content_type=ContentType.m_part_form_data, min_length=1),
) -> ...: