from rapidy import Rapidy
from rapidy.http import Body, get, post

from benchmarks.common.models import UserIn, UserOut


@post('/users')
async def create_user(user: UserIn = Body()) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, tags=user.tags)


@get('/health')
async def health() -> str:
    return 'ok'


app = Rapidy(http_route_handlers=[create_user, health])
