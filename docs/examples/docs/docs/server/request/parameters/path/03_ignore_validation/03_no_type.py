@get('/')
async def handler_1(
    user_id=PathParam()
) -> ...:
    # ...

@get('/')
async def handler_2(
    path_data=PathParams()
) -> ...:
    # {'user_id': ..., 'user_data': ...}