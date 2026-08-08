from rapidy.http import get, PathParam, PathParams

@get('/')
async def handler_1(
    user_id: int = PathParam(validate=False)
) -> ...:
    # ...

@get('/')
async def handler_2(
    path_data: int = PathParams(validate=False)
) -> ...:
    # {'user_id': ..., 'user_data': ...}