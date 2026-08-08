from rapidy.enums import Charset

@get(
    '/',
    response_charset=Charset.utf8,
)
async def handler() -> str:
    return 'hello, rapidy!'