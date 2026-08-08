from rapidy.http import get, Header, Request

@get('/')
async def handler(
        host: str = Header(alias='Host'),
        *,
        request: Request,
) -> ...: