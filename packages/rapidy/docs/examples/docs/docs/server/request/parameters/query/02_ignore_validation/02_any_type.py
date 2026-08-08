from typing import Any

@get('/')
async def handler_1(
    query: Any = QueryParam(),
) -> ...:
    # ...

@get('/')
async def handler_2(
    query_params_data: Any = QueryParams(),
) -> ...:
    # <MultiDictProxy('query': ..., 'star_rating', ...)>