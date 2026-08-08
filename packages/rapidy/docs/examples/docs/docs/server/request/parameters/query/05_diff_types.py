@get('/')
async def handler(
    query: str = QueryParam(),
    query_params_data: QueryParamsData = QueryParams(),
) -> ...: