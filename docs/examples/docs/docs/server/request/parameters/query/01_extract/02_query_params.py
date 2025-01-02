from rapidy.http import get, QueryParam

@get('/')
async def handler(
    query: str = QueryParam(),
    star_rating: str = QueryParam(),
) -> ...: