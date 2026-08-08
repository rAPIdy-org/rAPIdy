...
@get(
    '/',
    response_exclude_unset=True,
)
async def handler() -> Result:
    return Result(someAnotherValue='new_data')  # {"someAnotherValue": "new_data"}