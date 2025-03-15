@get('/')
async def handler_1(
    query=QueryParam(),
) -> ...:
    # ...

@get('/')
async def handler_2(
    query_params_data=QueryParams(),
) -> ...:
    # <MultiDictProxy('query': ..., 'star_rating', ...)>