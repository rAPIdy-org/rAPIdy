from rapidy.http import get, ContentType

@get(
    '/',
    content_type=ContentType.text_any,
)
async def handler() -> str:
    return 'hello rapidy!'  # "hello rapidy!"
