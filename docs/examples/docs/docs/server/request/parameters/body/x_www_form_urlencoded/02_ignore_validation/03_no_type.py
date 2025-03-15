@post('/')
async def handler(
    data = Body(content_type=ContentType.x_www_form),
) -> ...: