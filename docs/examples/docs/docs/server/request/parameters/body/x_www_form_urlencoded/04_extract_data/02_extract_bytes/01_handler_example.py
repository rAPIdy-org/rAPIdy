@post('/')
async def handler(
    user_data: bytes = Body(content_type=ContentType.x_www_form),
    # also you can use pydantic validation
    user_data: bytes = Body(content_type=ContentType.x_www_form, min_length=1),
) -> ...: