@post('/')
async def handler(
    data: bytes | None = Body(content_type=ContentType.stream),
    # or
    data: Optional[bytes] = Body(content_type=ContentType.stream),
    # or
    data: Union[bytes, None] = Body(content_type=ContentType.stream),
) -> ...: