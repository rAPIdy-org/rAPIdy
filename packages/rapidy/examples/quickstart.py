from typing import Annotated

from pydantic import BaseModel

from rapidy import Rapidy, run_app
from rapidy.http import Body, get, post


class UserIn(BaseModel):
    """Validated request payload."""

    name: str
    age: int


class UserOut(UserIn):
    """Serialized response payload."""

    id: int


@get('/')
async def hello() -> dict[str, str]:
    """Return a minimal JSON response."""
    return {'message': 'Hello, rAPIdy 2.0!'}


@post('/users', status_code=201)
async def create_user(user: Annotated[UserIn, Body()]) -> UserOut:
    """Validate a user and return a response model."""
    return UserOut(id=1, **user.model_dump())


app = Rapidy(http_route_handlers=[hello, create_user])


if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000)
