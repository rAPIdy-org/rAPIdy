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
An authenticated identity without required scopes returns HTTP 403. The OpenAPI JSON and UI routes are public by
default, so a global policy does not lock clients out of the authentication description. Set
`OpenAPIConfig(public=False)` when the schema and UI must inherit the same runtime policy.

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
Repeated `Authorization` fields and repeated header/query API-key parameters are rejected with HTTP 401, regardless
of value order, so authentication cannot disagree with handler parameter extraction.

`Response.set_cookie()` defaults to `SameSite=Lax`. For authentication cookies, explicitly set `secure=True` and
`httponly=True` (and choose `lax` or `strict` for the application flow); those flags cannot be inferred safely for
generic cookies or local HTTP development.

## Request, WebSocket, and DI

HTTP handlers receive `request.user`, `request.auth`, and `request.identity`. WebSocket handlers get the same values
from both the synthetic `Request` and `WebSocket`; a rejected handshake closes with WebSocket code 1008.

HTTP middleware is not executed for WebSocket connections: `CORSMiddleware`, `TrustedHostMiddleware`, proxy/header,
redirect, compression, and request-ID behavior is HTTP-only. Configure handshake Host/Origin checks explicitly with
`WebSocketSecurityConfig`; application/router/route guards remain available for additional WebSocket authorization.

```python
from rapidy.security import APIKeyAuth, SecurityConfig, WebSocketSecurityConfig


session_cookie = APIKeyAuth(
    name='sessionCookie',
    parameter_name='session',
    location='cookie',
    verify=verify_session,
)
security = SecurityConfig(
    schemes=[session_cookie],
    websocket=WebSocketSecurityConfig(
        allowed_hosts=('api.example.com',),
        allowed_origins=('https://app.example.com',),
    ),
)
```

Host patterns use the same exact/`*.example.com` semantics as `TrustedHostMiddleware`; ports are ignored for matching.
Origins are exact serialized origins. Missing, malformed, or duplicate Host/Origin values fail closed when that check
is configured. `allow_missing_origin=True` is available for non-browser clients, and `*` can opt into any valid
origin. Neither option is accepted as protection for a WebSocket route that references a cookie API-key scheme:
cookie-authenticated handshakes require an explicit, non-`null`, non-wildcard origin list and a present Origin header
to prevent Cross-Site WebSocket Hijacking (CSWSH).

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
