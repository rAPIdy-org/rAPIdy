@get(
    '/',
    allow_head=True,
)
async def handler() -> str:
    return 'ok'
