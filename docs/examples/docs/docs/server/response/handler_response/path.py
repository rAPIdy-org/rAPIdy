from rapidy.http import get

@get(
    '/',
)
async def handler() -> ...:
    ...