from rapidy.http import get, Response

@get('/')
async def handler(response: Response) -> ...:
    ...