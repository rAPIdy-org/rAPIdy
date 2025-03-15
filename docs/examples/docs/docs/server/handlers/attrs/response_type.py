@get(
    '/',
    response_type=dict[str, str],  # <-- `dict[str, str]` will be used for validation
)
async def handler() -> str:  # <-- `str` will be ignored
    return {'hello': 'rapidy'}