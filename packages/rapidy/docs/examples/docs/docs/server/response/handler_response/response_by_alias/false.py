...
@get(
    '/',
    response_by_alias=False,
)
async def handler() -> Result:
    return Result()  # {"value": "data"}