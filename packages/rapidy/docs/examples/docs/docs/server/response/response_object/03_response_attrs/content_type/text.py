from rapidy.http import get, Response, ContentType

@get('/')
async def handler() -> Response:
    return Response(
        text='hello rapidy!',
        content_type=ContentType.text_any,
    )  # "hello rapidy!"