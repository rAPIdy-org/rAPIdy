from rapidy import Rapidy
from rapidy.http import post, Body
from pydantic import BaseModel

class UserData(BaseModel):
    name: str
    age: int

@post('/user')
async def create_user(user: UserData = Body()) -> dict[str, str]:
    return {'message': f'User {user.name}, {user.age} years old'}

async def on_startup() -> None:
    print("App is starting...")

rapidy = Rapidy(
    http_route_handlers=[create_user],
    on_startup=[on_startup],
)