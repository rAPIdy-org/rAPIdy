@post('/')
async def handler(
    data = Body(content_type=ContentType.text_plain),
) -> ...: