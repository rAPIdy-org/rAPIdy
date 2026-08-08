@post('/')
async def handler(
    data: Any = Body(content_type=ContentType.text_plain),
) -> ...: