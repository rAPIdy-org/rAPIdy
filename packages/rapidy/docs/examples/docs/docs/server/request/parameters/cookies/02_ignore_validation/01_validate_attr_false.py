from rapidy.http import get, Cookie, Cookies

@get('/')
async def handler_1(
    user_id: int = Cookie(alias='UserID', validate=False)
) -> ...:
    # ...

@get('/')
async def handler_2(
    cookie_data: int = Cookies(validate=False)
) -> ...:
    # # {'UserID': ..., 'User-Session': ...}