from typing import Annotated

@get('/')
async def handler(
    some_query_param: Annotated[str, QueryParam()] = 'SomeValue',
) -> None: