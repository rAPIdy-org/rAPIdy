from rapidy.http import Header, Cookie, QueryParam, ..., Body

async def handler(
    user_id: int = QueryParam(),
) -> ...:
    ...