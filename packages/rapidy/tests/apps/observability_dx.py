from __future__ import annotations

from rapidy import Rapidy
from rapidy.http import get, PathParam
from rapidy.openapi import OpenAPIConfig


@get('/health', name='health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@get('/users/{user_id:\\d+}', name='user')
async def user(user_id: int = PathParam()) -> dict[str, int]:
    return {'user_id': user_id}


app = Rapidy(
    http_route_handlers=[health, user],
    openapi_config=OpenAPIConfig.docs(title='Observability DX', version='1'),
)
