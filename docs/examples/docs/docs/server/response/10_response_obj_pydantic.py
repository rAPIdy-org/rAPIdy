from rapidy.http import get, Response

@get('/')
async def handler(
) -> int:  # <-- `int` type to validate will be ignored
    return Response()