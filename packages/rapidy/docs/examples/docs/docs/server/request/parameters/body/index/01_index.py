from pydantic import BaseModel
from rapidy.http import post, Body

class UserData(BaseModel):
    username: str
    password: str

@post('/')
async def handler(
    user_data: UserData = Body(),
) -> ...: