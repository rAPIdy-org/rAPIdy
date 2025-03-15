from rapidy.http import Response, get

@get('/')
async def handler() -> Response:
    return Response(
        status=201,
    )