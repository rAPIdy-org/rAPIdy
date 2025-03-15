from rapidy.http import get, PathParam

@get('/{user_id}/{user_data}')
async def handler(
    user_id: str = PathParam(),
    user_data: str = PathParam(),
) -> ...: