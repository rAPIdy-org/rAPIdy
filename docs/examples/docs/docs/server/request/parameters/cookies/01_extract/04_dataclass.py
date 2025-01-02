from dataclasses import dataclass
from rapidy.http import get, Cookies

@dataclass
class CookieData:
    UserID: str  # camelCase syntax if cookie name is 'UserID'
    user_session: str  # cannot extract if cookie name is 'User-Session'

@get('/')
async def handler(
    cookie_data: CookieData = Cookies(),
) -> ...:
# {"errors": [{"type": "missing", "loc": ["cookie", "user_session"], "msg": "Field required"}]}