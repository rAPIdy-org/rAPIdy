@post('/')
async def handler(
    data=Body(content_type=ContentType.stream),
) -> ...: