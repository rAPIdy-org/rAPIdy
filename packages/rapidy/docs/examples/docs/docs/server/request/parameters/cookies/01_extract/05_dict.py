from rapidy.http import get, Cookies

@get('/')
async def handler(
    cookie_data: dict[str, str] = Cookies(),
) -> ...:
# {'UserID': ..., 'User-Session': ...}