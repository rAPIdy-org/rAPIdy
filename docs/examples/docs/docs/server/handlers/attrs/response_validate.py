@get(
    '/',
    response_validate=False,
)
async def handler() -> str:  # <-- `str` will be ignored
    return {'hello': 'rapidy'}