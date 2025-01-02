from typing import Any

@get('/')
async def handler_1(
    user_id: Any = Cookie(alias='UserID', validate=False)
) -> ...:
    # ...

@get('/')
async def handler_2(
    cookie_data: Any = Cookies(validate=False)
) -> ...:
    # # {'UserID': ..., 'User-Session': ...}