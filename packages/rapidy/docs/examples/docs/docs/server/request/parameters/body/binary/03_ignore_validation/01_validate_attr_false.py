@post('/')
async def handler(
    data: SomeBytesType = Body(validate=False, content_type=ContentType.stream),
) -> ...: