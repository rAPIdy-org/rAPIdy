from rapidy.http import get, Header

@get('/')
async def handler(
    host: str = Header(alias='Host'),
    keep_alive: str = Header(alias='Keep-Alive'),
) -> ...: