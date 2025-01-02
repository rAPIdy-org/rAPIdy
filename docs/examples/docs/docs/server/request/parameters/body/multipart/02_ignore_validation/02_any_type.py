@post('/')
async def handler(
    data: Any = Body(content_type=ContentType.m_part_form_data),
) -> ...: