from rapidy.http import get, QueryParam, QueryParams

@get('/')
async def handler_1(
    query: int = QueryParam(validate=False)
) -> ...:
    # ...

@get('/')
async def handler_2(
    query_params_data: int = QueryParams(validate=False)
) -> ...:
    # <MultiDictProxy('query': ..., 'star_rating', ...)>