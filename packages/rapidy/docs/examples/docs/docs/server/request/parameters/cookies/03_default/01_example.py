@get('/')
async def handler(
    some_cookie: str = Cookie(alias='Some-Cookie', default='SomeValue'),
) -> ...: