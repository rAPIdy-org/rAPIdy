from rapidy.http import post, Body, ContentType

@post('/')
async def handler(
    user_data: bytes = Body(),
    # or use any content_type
    user_data: bytes = Body(content_type=ContentType.stream),
    # also you can use pydantic validation
    user_data: bytes = Body(min_length=1),
) -> ...: