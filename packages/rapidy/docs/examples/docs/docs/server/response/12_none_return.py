from rapidy.http import get, Response

@get('/')
async def handler(response: Response) -> None:
    response.text = 'hello rapidy!'

# success response --> `hello rapidy!`