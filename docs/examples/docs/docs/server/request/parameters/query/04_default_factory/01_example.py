@get('/')
async def handler(
    some_query_param: str = QueryParam(default_factory=lambda: 'SomeValue'),
) -> None: