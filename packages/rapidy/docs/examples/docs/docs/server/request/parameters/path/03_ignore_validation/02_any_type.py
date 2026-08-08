from typing import Any

@get('/')
async def handler_1(
    user_id: Any = PathParam()
) -> ...:
    # "0.0.0.0:8080"

@get('/')
async def handler_2(
    path_data: Any = PathParams()
) -> ...:
    # {'user_id': ..., 'user_data': ...}