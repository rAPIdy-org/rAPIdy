from __future__ import annotations

import os

from rapidy import Rapidy, run_app
from rapidy.depends import FromDI
from rapidy.http import get, Request
from rapidy.openapi import OpenAPIConfig
from rapidy.security import (
    APIKeyAuth,
    AuthCredentials,
    constant_time_compare,
    SecurityConfig,
    SecurityIdentity,
    SimpleUser,
)


async def verify_api_key(supplied: str) -> SimpleUser | None:
    """Resolve one API key without exposing the configured value."""
    expected = os.environ.get('ITEMS_API_KEY')
    if expected is None or not constant_time_compare(supplied, expected):
        return None
    return SimpleUser('items-service')


security = SecurityConfig(
    schemes=[
        APIKeyAuth(
            verify=verify_api_key,
            scopes=['items:read'],
        )
    ],
    requirements=[{'apiKey': ['items:read']}],
)


@get('/items')
async def items(
    request: Request,
    identity: FromDI[SecurityIdentity],
    credentials: FromDI[AuthCredentials],
) -> dict[str, object]:
    """Return protected data and the established identity."""
    return {
        'items': ['one', 'two'],
        'identity_matches_request': identity is request.identity,
        'user': identity.user.display_name,
        'scopes': sorted(credentials.scopes),
    }


@get('/health', public=True)
async def health() -> str:
    """Remain reachable without credentials or inherited guards."""
    return 'ok'


app = Rapidy(
    security=security,
    openapi_config=OpenAPIConfig(title='Secured items', version='1.0.0'),
    http_route_handlers=[items, health],
)


if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000)
