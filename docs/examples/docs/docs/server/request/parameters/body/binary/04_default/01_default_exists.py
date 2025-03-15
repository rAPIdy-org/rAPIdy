@post('/')
async def handler(
    data: bytes = Body(b'some_bytes', content_type=ContentType.stream),
    # or
    data: bytes = Body(default_factory=lambda: b'some_bytes', content_type=ContentType.stream),
) -> ...: