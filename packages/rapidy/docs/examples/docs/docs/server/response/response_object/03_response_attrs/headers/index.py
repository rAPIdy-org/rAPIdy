from rapidy.http import Response, get

@get('/')
async def handler() -> Response:
    return Response(
        headers={'Some-Header': '123'},
    )
