from rapidy.http import get, Response, ContentType

@get('/')
async def handler() -> Response:
    return Response(
        body={'hello': 'rapidy!'},
        content_type=ContentType.json,
    )  # {"hello": "rapidy!"}
