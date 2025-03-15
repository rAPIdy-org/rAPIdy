from rapidy.http import get, Response

@get('/')
async def handler(
    response: Response,  # <-- this response will be returned
) -> str:
    return 'ok'