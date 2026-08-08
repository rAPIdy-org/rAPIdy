from rapidy.http import get

@get(
    '/',
    # `dict[str, str]` will be used for validate and serialize body response data
    response_type=dict[str, str],
)
async def handler() -> str:  # <-- `str` will be ignored
    return {'hello': 'rapidy'}