...
@get('/')
async def handler() -> ...:
    response = Response()
    response.del_cookie('SomeCookie')
    ...