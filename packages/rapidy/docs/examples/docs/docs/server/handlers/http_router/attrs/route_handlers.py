from rapidy.http import get, HTTPRouter

@get('/hello')  # /api/hello
async def hello_handler() -> str:
    return 'hello rapidy!'

router = HTTPRouter(
    path='/api',
    route_handlers=[hello_handler],
)