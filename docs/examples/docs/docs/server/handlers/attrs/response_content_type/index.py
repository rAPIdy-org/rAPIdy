from rapidy.enums import ContentType

@get(
    '/',
    response_content_type=ContentType.text_plain,
)
async def handler() -> str:
    return 'hello, rapidy!'