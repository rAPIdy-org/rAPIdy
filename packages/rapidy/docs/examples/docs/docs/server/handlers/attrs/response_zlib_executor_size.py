@get(
    '/',
    response_zlib_executor_size=1024,
)
async def handler() -> str:
    return 'hello, rapidy!'