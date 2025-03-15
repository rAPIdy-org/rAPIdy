from rapidy.http import get, Response, ContentType

@get('/')
async def handler() -> Response:
    return Response(
        body={'hello': 'rapidy!'},
        content_type=ContentType.json,
        # or
        content_type='application/json',
    )

@get('/')
async def handler() -> dict[str, str]:
    response = Response()

    response.content_type = ContentType.json
    # or
    response.content_type = 'application/json'

    return {'hello': 'rapidy!'}

@get('/')
async def handler(response: Response) -> dict[str, str]:
    response.content_type = ContentType.json
    # or
    response.content_type = 'application/json'

    return {'hello': 'rapidy!'}
