from rapidy.http import get, ContentType

@get(
    '/',
    response_content_type=ContentType.json,
)
async def handler() -> str:
    return 'hello rapidy!'  # "'hello rapidy!'"
