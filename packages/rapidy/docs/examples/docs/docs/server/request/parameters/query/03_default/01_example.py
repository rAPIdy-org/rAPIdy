@get('/')
async def handler(
    some_query_param: str = QueryParam(default='SomeValue'),
) -> None: