from rapidy.http import Response, get

@get('/')
async def handler() -> Response:
    return Response(
        text = 'hello rapidy',
    )

@get('/')
async def handler() -> ...:
    response = Response()
    response.text = 'hello rapidy'
    ...

@get('/')
async def handler(response: Response) -> ...:
    response.text = 'hello rapidy'
    ...