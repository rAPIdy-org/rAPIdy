@get('/')
async def handler_1(
    user_id=Cookie(alias='UserID')
) -> ...:
    # ...

@get('/')
async def handler_2(
    cookie_data=Cookies()
) -> ...:
    # # {'UserID': ..., 'User-Session': ...}