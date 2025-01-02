from pydantic import BaseModel, Field
from rapidy.http import get, Cookies

class CookieData(BaseModel):
    user_id: str = Field(alias='UserID')
    user_session: str = Field(alias='User-Session')

@get('/')
async def handler(
    cookie_data: CookieData = Cookies(),
) -> ...: