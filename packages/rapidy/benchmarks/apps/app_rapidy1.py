from rapidy import Rapidy, run_app
from rapidy.http import Body, get, post

from benchmarks.common.models import UserIn, UserOut


@post('/users')
async def create_user(user: UserIn = Body()) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, tags=user.tags)


@get('/health')
async def health() -> str:
    return 'ok'


app = Rapidy(http_route_handlers=[create_user, health])

if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000, access_log=None)
