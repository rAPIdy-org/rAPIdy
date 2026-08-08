from rapidy.http import get, PathParam, Header

@get('/{user_id}')
async def handler(
    user_id: int = PathParam(),
    host: str = Header(alias='Host'),
) -> ...: