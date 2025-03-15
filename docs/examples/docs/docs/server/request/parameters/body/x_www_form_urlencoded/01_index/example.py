from pydantic import BaseModel
from rapidy.http import post, Body, ContentType

class UserData(BaseModel):
    username: str
    password: str

@post('/')
async def handler(
    user_data: UserData = Body(content_type=ContentType.x_www_form),
    # or
    user_data: UserData = Body(content_type='application/x-www-form-urlencoded'),
) -> ...: