from rapidy.http import get, PathParam

@get('/{user_id}')
async def handler(
    user_id: str = PathParam(),
) -> ...: