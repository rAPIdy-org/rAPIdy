from pydantic import BaseModel
from rapidy.http import get, Body

class UserData(BaseModel):
    name: str
    age: int

@get('/user')
async def handler(data: UserData = Body()) -> dict[str, str]:
    return {'message': f'User {data.name}, {data.age} years old'}