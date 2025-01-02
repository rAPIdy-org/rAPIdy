@get('/')
async def handler(
    query_params_data: QueryParamsData = QueryParams(alias='SomeName'),  # <-- alias not working
) -> ...: