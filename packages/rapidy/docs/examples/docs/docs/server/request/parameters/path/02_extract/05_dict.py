from rapidy.http import get, PathParams

@get('/{user_id}/{user_data}')
async def handler(
    path_data: dict[str, str] = PathParams(),
) -> ...:
# {'user_id': ..., 'user_data': ...}