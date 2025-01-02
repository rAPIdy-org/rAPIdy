from rapidy.http import get, Header

@get('/')
async def handler(
    host: str = Header(alias='Host'),
) -> ...: