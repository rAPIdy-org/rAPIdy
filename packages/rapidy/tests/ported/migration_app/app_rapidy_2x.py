from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel

from rapidy import Rapidy, run_app
from rapidy.depends import FromDI, inject_http, provide, Provider, Scope
from rapidy.http import Body, get, Header, HTTPRouter, middleware, PathParam, post, Request, Response
from rapidy.typedefs import CallNext


class Item(BaseModel):
    name: str
    quantity: int


class GreetingProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def greeting(self) -> str:
        return 'hello'


@post('/items')
async def create_item(item: Annotated[Item, Body()]) -> Item:
    return item


@get('/users/{user_id}')
@inject_http
async def read_user(
    greeting: FromDI[str],
    user_id: int = PathParam(),
    token: str = Header(alias='X-Token'),
) -> dict[str, object]:
    return {'greeting': greeting, 'user_id': user_id, 'token': token}


@middleware
async def add_migration_marker(request: Request, call_next: CallNext) -> Response:
    response = await call_next(request)
    response.headers['X-Migration'] = 'rapidy-2'
    return response


api = HTTPRouter('/v1', route_handlers=[read_user])
app = Rapidy(
    di_providers=[GreetingProvider()],
    middlewares=[add_migration_marker],
    http_route_handlers=[create_item, api],
)


if __name__ == '__main__':
    run_app(
        app,
        host='127.0.0.1',
        port=8000,
        workers=2,
        workers_kill_timeout=30,
    )
