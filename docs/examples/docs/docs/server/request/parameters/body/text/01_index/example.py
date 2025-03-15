from rapidy.http import post, Body, ContentType

@post('/')
async def handler(
    text_data: str = Body(content_type=ContentType.text_plain),
    # or
    text_data: str = Body(content_type=ContentType.text_html),
    # or any mime-type with type `text`
    text_data: str = Body(content_type=ContentType.text_any),
) -> ...: