from rapidy.http import get, ContentType, Response

@get(
    '/',
    response_content_type=ContentType.json,  # <-- will be ignored
)
async def handler() -> Response:
    return Response(...)