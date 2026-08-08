...
@get(
    '/',
    response_exclude_defaults=True,
)
async def handler() -> Result:
    return Result()  # {}