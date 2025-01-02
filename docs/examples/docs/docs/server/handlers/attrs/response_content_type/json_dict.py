from rapidy.http import get, ContentType

@get(
    '/',
    content_type=ContentType.json,
)
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy!'}  # {"hello": "rapidy!"}
