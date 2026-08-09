<p align="center">
  <img src="https://raw.githubusercontent.com/rAPIdy-org/rAPIdy/main/packages/rapidy/docs/docs/assets/logo-teal.png" alt="rAPIdy" width="420">
</p>

# rAPIdy 2.0

rAPIdy is an async-first ASGI framework with Pydantic v2 validation, dependency injection, middleware, mounts,
WebSockets, Server-Sent Events, and streaming responses. Version 2.0 no longer depends on aiohttp: Granian is the
default server, while Uvicorn and Hypercorn are supported through optional extras.

- Python 3.12+
- Pydantic `>=2.9,<3`
- Typed package with `py.typed`
- Preserves the `import rapidy` application API from 1.x

## Install

After the 2.0 packages are published:

```bash
python -m pip install "rapidy[granian]"
```

From this repository before publication, install core first:

```bash
python -m pip install -e packages/rapidy_core
python -m pip install -e "packages/rapidy[granian]"
```

Use `rapidy[uvicorn]` or `rapidy[hypercorn]` if that server is your deployment target.
Install `rapidy[test]` for the public HTTP/WebSocket/SSE testing clients.

## Quickstart

```python
from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.http import Body, get, post


class UserIn(BaseModel):
    name: str
    age: int


@get('/')
async def hello() -> dict[str, str]:
    return {'message': 'Hello, rAPIdy 2.0!'}


@post('/users', status_code=201)
async def create_user(user: UserIn = Body()) -> UserIn:
    return user


app = Rapidy(http_route_handlers=[hello, create_user])
```

Enable OpenAPI 3.1 and interactive documentation explicitly:

```python
from rapidy.openapi import OpenAPIConfig

app = Rapidy(
    http_route_handlers=[hello, create_user],
    openapi_config=OpenAPIConfig(title='Users API', version='1.0.0'),
)
```

The schema is served at `/schema/openapi.json`, Swagger UI at `/schema`, and ReDoc at `/schema/redoc`. Request and
response schemas come from the same Pydantic annotations used for runtime validation. Reusable components,
callbacks, webhooks, and response links use their native OpenAPI 3.1 object shapes. UI render plugins can use CDN,
internal-host, or application-local asset URLs and support custom renderers without adding runtime dependencies.

Runtime authentication and OpenAPI can share one contract:

```python
from rapidy.security import APIKeyAuth, SecurityConfig

security = SecurityConfig(
    schemes=[APIKeyAuth(key=settings.api_key)],
    requirements=[{'apiKey': []}],
)
app = Rapidy(
    security=security,
    openapi_config=OpenAPIConfig(title='Users API', version='1.0.0'),
)
```

Built-in API-key, Basic, and opaque Bearer schemes cover HTTP and WebSocket. Scopes, cumulative guards, public route
overrides, `request.user`/`request.auth`, and typed DI are included without adding a cryptography dependency.

Run it with Granian:

```bash
granian --interface asgi --host 127.0.0.1 --port 8000 main:app
```

Or keep a Python entry point:

```python
from rapidy import run_app

if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000, workers=1)
```

The complete executable version is in [`examples/quickstart.py`](examples/quickstart.py).

## Request sources

Handler parameters declare where values come from. Pydantic validates the converted values and invalid input returns
HTTP 422 with an `errors` list.

```python
from rapidy.http import Body, Cookie, Header, PathParam, QueryParam, post


@post('/users/{user_id}')
async def update_user(
    payload: UserIn = Body(),
    user_id: int = PathParam(),
    token: str = Header(alias='X-Token'),
    page: int = QueryParam(alias='page'),
    session: str = Cookie(),
) -> dict[str, object]:
    return {'user_id': user_id, 'name': payload.name, 'page': page}
```

JSON, text, bytes, urlencoded forms, and multipart uploads are supported. Raw access remains available through
`Request.read()`, `Request.text()`, `Request.json()`, and `Request.post()`.

## Testing

```python
from rapidy.testing import TestClient


def test_hello() -> None:
    with TestClient(app) as client:
        response = client.get('/')

    assert response.json() == {'message': 'Hello, rAPIdy 2.0!'}
```

`AsyncTestClient` provides the asynchronous HTTPX API. Both clients own application lifespan inside their context and
provide in-process WebSocket/SSE sessions plus isolated Dishka provider overrides.

## Framework features

- Dependency injection is exposed from `rapidy.depends`; application singletons are process-local, request resources
  are finalized after the response is sent, and WebSocket resources use `Scope.SESSION`.
- `@middleware` can extract and validate request parameters and accepts the same `response_*` serialization options
  as HTTP handlers.
- OpenAPI 3.1 generation is available from `rapidy.openapi`, including Pydantic components, request bodies,
  parameters, responses, all reusable component sections, callbacks, webhooks, response links, mounted routes,
  Swagger UI, and ReDoc.
- Runtime security from `rapidy.security` shares schemes and requirements with OpenAPI and exposes identities through
  HTTP, WebSocket, and DI.
- `HTTPRouter('/v1', handlers)` creates nested mounts with their own middleware, limits, and lifespan while sharing
  the root DI container.
- `@websocket`, `WebSocket`, `SSEResponse`, and `StreamResponse` provide native ASGI realtime and streaming APIs.
- `rapidy.testing` provides sync/async HTTPX clients, lifespan, DI overrides, WebSocket, and incremental SSE testing.
- Type checking uses `plugins = rapidy_core.mypy`; there is no `rapidy.mypy` package in 2.0.

Executable examples live in [`examples/`](examples/), and the full guide is published at
[rapidy.dev](https://rapidy.dev).

## Deployment

```bash
# Granian (recommended)
granian --interface asgi --workers 4 --workers-kill-timeout 30s main:app

# Uvicorn
uvicorn main:app --workers 4

# Hypercorn
hypercorn --workers 4 main:app
```

Each worker has its own application lifespan and DI container, so application-scoped dependencies are per-process.
Choose graceful-shutdown timeouts long enough for active streaming responses; rAPIdy closes accepted WebSockets with
code 1001 during shutdown.

## Migration and performance

- [1.x → 2.0 migration guide](https://github.com/rAPIdy-org/rAPIdy/blob/main/MIGRATION.md): `import rapidy` stays;
  the transport layer and dropped aiohttp-specific APIs are the breaking changes.
- [Reproducible benchmark method and results](benchmarks/RESULTS.md): raw JSON, RPS, p50/p95/p99, and CV are checked
  in. The report explicitly records both wins and losses; it does not make unsupported marketing claims.

## License

MIT. See [`LICENSE`](LICENSE).
