from rapidy.http import QueryParam

async def handler(
    test_query_param_name: int = QueryParam(),
) -> int:
    return test_query_param_name