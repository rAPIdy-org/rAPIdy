# Authentication and authorization

`SecurityConfig` is the single source for runtime authentication and OpenAPI security metadata. A scheme combines
an `AuthBackend` with its OpenAPI definition; a requirement uses the native OpenAPI shape.

```python
import os

from rapidy import Rapidy
from rapidy.http import get, Request
from rapidy.openapi import OpenAPIConfig
from rapidy.security import APIKeyAuth, SecurityConfig, SimpleUser


api_key = APIKeyAuth(
    key=os.environ['ITEMS_API_KEY'],
    user=SimpleUser('items-service'),
    scopes=['items:read'],
)
security = SecurityConfig(
    schemes=[api_key],
    requirements=[{'apiKey': ['items:read']}],
)


@get('/items')
async def items(request: Request) -> dict[str, str]:
    return {'user': request.user.display_name}


@get('/health', public=True)
async def health() -> str:
    return 'ok'


app = Rapidy(
    security=security,
    openapi_config=OpenAPIConfig(title='Items API', version='1'),
    http_route_handlers=[items, health],
)
```

Missing or invalid credentials return HTTP 401 and a `WWW-Authenticate` challenge when the scheme provides one.
An authenticated identity without required scopes returns HTTP 403. The OpenAPI JSON and UI routes are explicitly
public, so a global policy does not lock clients out of the authentication description.

## Requirements and inheritance

Requirements follow OpenAPI semantics:

- separate mappings are alternatives (OR): `security=[{'apiKey': []}, {'bearerAuth': []}]`;
- multiple schemes in one mapping are cumulative (AND): `security=[{'first': [], 'second': []}]`;
- scopes must all be present: `security=[{'bearerAuth': ['items:write']}]`;
- an empty mapping adds an anonymous alternative: `security=[{}, {'bearerAuth': []}]`;
- `security=[]` removes authentication for a route but keeps inherited guards;
- `public=True` explicitly removes both inherited authentication and guards.

Application policy is inherited by `HTTPRouter`. A router with its own `SecurityConfig` overrides the inherited
default requirement while retaining parent schemes and cumulative guards. Controller and handler guards are added
in application → router → controller → handler order.

```python
from rapidy.exceptions import HTTPForbidden


def staff_only(request: Request) -> None:
    if 'staff' not in request.auth.scopes:
        raise HTTPForbidden


@get('/admin', guards=[staff_only])
async def admin() -> str:
    return 'ok'
```

A guard may be synchronous or asynchronous. It should raise an HTTP exception; returning `False` is shorthand for
HTTP 403.

## Built-in schemes

- `APIKeyAuth` reads a header, query parameter, or cookie. A static `key=` uses constant-time comparison; `verify=`
  delegates lookup to sync or async application code.
- `BasicAuth` accepts a verifier or a static username/password pair. Static values use constant-time comparisons.
- `BearerAuth` extracts an opaque Bearer token and delegates verification to application code.

The base package deliberately has no JWT, JWK, OIDC, password-hashing, or cryptography dependency. Use a library of
your choice inside a Bearer verifier, or implement `AuthBackend` and bind it with `SecurityScheme`. Return
`SecurityIdentity` from a verifier when scopes are dynamic; returning any other non-`None` object uses the static
scopes configured on the built-in scheme.

Raw passwords, API keys, and Bearer tokens are never stored in `AuthCredentials`. Built-in scheme/backend `repr`
values omit secret material. Application verifiers remain responsible for safe logging and storage.

## Request, WebSocket, and DI

HTTP handlers receive `request.user`, `request.auth`, and `request.identity`. WebSocket handlers get the same values
from both the synthetic `Request` and `WebSocket`; a rejected handshake closes with WebSocket code 1008.

```python
from rapidy.depends import FromDI
from rapidy.security import AuthCredentials, SecurityIdentity


@get('/me')
async def me(
    identity: FromDI[SecurityIdentity],
    credentials: FromDI[AuthCredentials],
) -> dict[str, object]:
    return {
        'user': identity.user.display_name,
        'scopes': sorted(credentials.scopes),
    }
```

The identity is anonymous on public and optional requests. DI resolves it after runtime authentication, and no raw
credential becomes a container value.
