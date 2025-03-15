@get('/')
async def handler(
    user_id: str = Cookie(alias='UserID'),
    cookie_data: CookieData = Cookies(),
) -> ...: