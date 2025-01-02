from rapidy.http import get, QueryParams

@get('/')
async def handler(
    query_params_data: dict[str, str] = QueryParams(),
) -> ...:
# {'query': ..., 'star_rating': ...}