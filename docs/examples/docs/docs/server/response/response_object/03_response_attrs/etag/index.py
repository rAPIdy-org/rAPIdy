from rapidy.http import get, Response

@get('/')
async def handler() -> ...:
    response = Response()
    response.etag = '33a64df551425fcc55e4d42a148795d9f25f89d4'
    ...

@get('/')
async def handler(response: Response) -> ...:
    response.etag = '33a64df551425fcc55e4d42a148795d9f25f89d4'
    ...