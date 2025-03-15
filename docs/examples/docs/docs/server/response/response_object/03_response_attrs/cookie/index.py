from rapidy.http import Response, get

@get('/')
async def handler() -> ...:
    response = Response()
    response.set_cookie('SomeCookie', 'SomeValue')
    ...

@get('/')
async def handler(response: Response) -> ...:
    response.set_cookie('SomeCookie', 'SomeValue')
    ...
