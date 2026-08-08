@get('/')
async def handler(
    some_header: str = Header(alias='Some-Header', default='SomeValue'),
) -> ...: