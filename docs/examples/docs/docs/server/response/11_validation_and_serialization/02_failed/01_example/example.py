from rapidy.http import get

@get('/')
async def handler() -> int:  # <-- `int` will be used to validate
    return 'some_data'  # <-- will raise err