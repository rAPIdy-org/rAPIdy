from rapidy.http import get

@get('/')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}