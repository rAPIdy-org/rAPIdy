from rapidy.http import get, Charset

@get(
    '/',
    response_charset=Charset.utf32,
)
async def handler() -> ...:
    ...