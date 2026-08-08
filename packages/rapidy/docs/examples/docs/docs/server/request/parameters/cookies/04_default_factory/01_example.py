@get('/')
async def handler(
    some_cookie: str = Cookie(alias='Some-Cookie', default_factory=lambda: 'SomeValue'),
) -> ...: