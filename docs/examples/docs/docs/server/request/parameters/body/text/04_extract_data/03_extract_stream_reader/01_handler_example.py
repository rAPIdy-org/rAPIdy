from rapidy import StreamReader

@post('/')
async def handler(
    user_data: StreamReader = Body(content_type=ContentType.text_plain),
) -> ...: