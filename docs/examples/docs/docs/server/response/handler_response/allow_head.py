from rapidy.http import get

@get(
    '/',
    allow_head=True,
)
async def handler() -> ...:
    ...