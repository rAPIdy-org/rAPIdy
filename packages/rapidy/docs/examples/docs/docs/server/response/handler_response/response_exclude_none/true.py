...
@get(
    '/',
    response_exclude_none=True,
)
async def handler() -> Result:
    return Result()  # {"someValue": "data"}