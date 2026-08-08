from rapidy.http import get, Cookie

@get('/')
async def handler(
    user_id: str = Cookie(alias='UserID'),
    user_session: str = Cookie(alias='UserSession'),
) -> ...: