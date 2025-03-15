@get('/')
async def handler(
    cookie_data: CookieData = Cookies(alias='SomeName'),  # <-- alias not working
) -> ...: