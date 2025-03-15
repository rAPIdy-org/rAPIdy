from rapidy.http import get, ContentType

@get(
    '/',
    response_content_type=ContentType.text_any,
)
async def handler() -> str:
    return 'hello rapidy!'  # "hello rapidy!"
