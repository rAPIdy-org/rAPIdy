from rapidy.http import Response, get

@get('/')
async def handler() -> Response:
    return Response(
        body={'hello': 'rapidy'},
    )

@get('/')
async def handler() -> ...:
    response = Response()
    response.body = {'hello': 'rapidy'}
    ...

@get('/')
async def handler(response: Response) -> ...:
    response.body = {'hello': 'rapidy'}
    ...