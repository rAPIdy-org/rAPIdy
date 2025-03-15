@post('/')
async def handler(
    data=Body(content_type=ContentType.m_part_form_data),
) -> ...: