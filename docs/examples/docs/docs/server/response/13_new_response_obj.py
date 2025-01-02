from rapidy.http import get, Response

@get('/')
async def handler() -> Response:
    return Response(status=201)