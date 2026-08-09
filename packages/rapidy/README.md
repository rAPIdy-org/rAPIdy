<p align="center">
  <img src="https://raw.githubusercontent.com/rAPIdy-org/rAPIdy/main/packages/rapidy/docs/docs/assets/logo-teal.png" alt="rAPIdy" width="420">
</p>

# rAPIdy 2.0

rAPIdy is an async-first ASGI framework with Pydantic v2 validation, dependency injection, middleware, mounts,
WebSockets, Server-Sent Events, streaming responses, post-response tasks, and safe file serving. Version 2.0 no longer
depends on aiohttp or bundles an ASGI server. Uvicorn is the recommended launcher extra; Granian and Hypercorn remain
independent alternatives.

- Python 3.12+
- Pydantic `>=2.9,<3`
- Typed package with `py.typed`
- Preserves the `import rapidy` application API from 1.x

## Public imports

The root facade is intentionally small and stable: import `Rapidy` and
`run_app` from `rapidy`; import HTTP handlers and markers from `rapidy.http`,
and use the owned `rapidy.security`, `rapidy.testing`, `rapidy.openapi`, and
`rapidy.middlewares` facades for those features. Names from `rapidy_client`
belong to the outbound-client domain and are not re-exported by the server.

## Install

```bash
python -m pip install rapidy
```

The base install is server-neutral. For the built-in `rapidy run` and `rapidy dev` commands:

```bash
python -m pip install "rapidy[uvicorn]"
```

For editable development from a repository checkout, install the workspace packages:

```bash
python -m pip install -e packages/rapidy_core
python -m pip install -e "packages/rapidy[uvicorn]"
```

Use `rapidy[granian]` or `rapidy[hypercorn]` instead if that server is your deployment target; these extras do not
install Uvicorn.
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

The schema is served at `/schema/openapi.json`, Swagger UI at `/schema`, and ReDoc at `/schema/redoc`. Use
`OpenAPIConfig.docs(title='Users API', version='1.0.0')` for the conventional opt-in `/openapi.json`, `/docs`, and
`/redoc` paths. Request and
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

Run it with the included Uvicorn server:

```bash
rapidy dev main:app
```

Or keep a Python entry point:

```python
from rapidy import run_app

if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000, workers=1)
```

The complete executable version is in
[`examples/quickstart.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/quickstart.py).

The built-in CLI adds development reload, route introspection, and configuration diagnostics:

```bash
rapidy dev main:app --reload
rapidy run main:app --host 0.0.0.0 --port 8080
rapidy routes main:app
rapidy check main:app
```

## Observability and reverse routing

Routes can be named and reversed without interpolating templates manually:

```python
@get('/users/{user_id:\\d+}', name='user.detail')
async def user(user_id: int = PathParam()) -> dict[str, int]:
    return {'id': user_id}

path = app.url_for('user.detail', user_id=42)
```

`request.url_for(...)` includes the deployment `root_path`; named static trees expose `app.static_url(...)`.
`AccessLogMiddleware` emits redacted records keyed by route template, while `ProblemDetailsRenderer` plugs into the
application-local `exception_handlers` registry. Install `rapidy[otel]` and call `instrument_app(...)` for HTTP/WS
spans and metrics through the official OpenTelemetry ASGI instrumentation. See
[`examples/observability_dx.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/observability_dx.py).

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

JSON, text, bytes, urlencoded forms, and multipart uploads are supported. Ordinary and raw request bodies are limited
to 1 MiB by default; multipart has separate configurable limits. Raw access remains available through
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
- Production middleware in `rapidy.middlewares` provides validated CORS/PNA, trusted hosts, HTTPS redirects,
  trusted proxy headers, request IDs with async context, and real gzip/optional Brotli compression.
- OpenAPI 3.1 generation is available from `rapidy.openapi`, including Pydantic components, request bodies,
  parameters, responses, all reusable component sections, callbacks, webhooks, response links, mounted routes,
  Swagger UI, and ReDoc.
- Runtime security from `rapidy.security` shares schemes and requirements with OpenAPI and exposes identities through
  HTTP, WebSocket, and DI.
- `HTTPRouter('/v1', handlers)` creates nested mounts with their own middleware, limits, and lifespan while sharing
  the root DI container.
- `@websocket`, `WebSocket`, `SSEResponse`, and `StreamResponse` provide native ASGI realtime and streaming APIs.
- `rapidy.background`, `FileResponse`, and `StaticFiles` provide ordered post-response work, conditional/range file
  responses, and traversal-safe mounted assets with optional ASGI zero-copy extensions.
- `rapidy.testing` provides sync/async HTTPX clients, lifespan, DI overrides, WebSocket, and incremental SSE testing.
- Type checking uses `plugins = rapidy_core.mypy`; there is no `rapidy.mypy` package in 2.0.

Executable examples live in
[`packages/rapidy/examples`](https://github.com/rAPIdy-org/rAPIdy/tree/main/packages/rapidy/examples), and the full guide is published at
[rapidy.dev](https://rapidy.dev).

## Deployment

```bash
# Uvicorn (recommended CLI runtime)
rapidy run main:app --workers 4 --timeout-graceful-shutdown 30

# Granian (optional)
granian --interface asgi --workers 4 --workers-kill-timeout 30s main:app

# Hypercorn
hypercorn --workers 4 main:app
```

Each worker has its own application lifespan and DI container, so application-scoped dependencies are per-process.
Choose graceful-shutdown timeouts long enough for active streaming responses. During direct application-lifespan
shutdown rAPIdy requests code 1001 for still-open WebSockets; a process server may close connections earlier with
its own restart code. Real-server behavior is therefore covered separately for every supported runtime.

## Migration and performance

- [1.x → 2.0 migration guide](https://github.com/rAPIdy-org/rAPIdy/blob/main/MIGRATION.md): `import rapidy` stays;
  the transport layer and dropped aiohttp-specific APIs are the breaking changes.
- [Reproducible benchmark method and results](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/benchmarks/RESULTS.md): raw JSON, RPS, p50/p95/p99, and CV are checked
  in. The report explicitly records both wins and losses; it does not make unsupported marketing claims.

## License

MIT. See the [license](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/LICENSE).
