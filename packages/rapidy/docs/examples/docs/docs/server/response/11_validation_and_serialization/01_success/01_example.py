@post('/')
async def handler() -> int:  # <-- `int` will be used to validate
    return '123'  # success response --> `123`