from concurrent.futures import Executor

class SomeExecutor(Executor):
    ...

@get(
    '/',
    response_zlib_executor=SomeExecutor,
)
async def handler() -> str:
    return 'hello, rapidy!'