@post('/')
async def handler(
    user_data: bytes = Body(content_type=ContentType.text_plain),
    # also you can use pydantic validation
    user_data: bytes = Body(content_type=ContentType.text_plain, min_length=1),
) -> ...: