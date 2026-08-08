# Migrating from rAPIdy 1.x

The central compatibility rule is simple: **`import rapidy` stays**. Models, handlers, decorators, middleware,
providers, and `HTTPRouter` can often remain byte-for-byte identical. The breaking changes are the transport layer and
aiohttp-specific APIs.

Read the complete, executable before/after guide in
[`MIGRATION.md`](https://github.com/rAPIdy-org/rAPIdy/blob/main/MIGRATION.md).

## Main changes

| 1.x | 2.0 |
|---|---|
| aiohttp `Request`/`Response` internals | Native ASGI rAPIdy objects |
| `request['key']` | `request.state.key` |
| aiohttp `run_app` options | Granian `workers` / `workers_kill_timeout` |
| aiohttp Gunicorn worker | Granian/Uvicorn/Hypercorn worker processes |
| `WebSocketResponse` inside `@get` | `@websocket` and `WebSocket` |
| `cleanup_ctx` | `app.lifespan.append(...)` |
| `app.router.*` / `add_routes` | decorators and `add_http_router(s)` |
| streaming request injection | cached `Request.read/text/json/post` |
| static files / background tasks | external server/service; no 2.0 equivalent |
| `AppKey` | `app.state` / `request.state` |
| `rapidy.mypy` | `rapidy_core.mypy` |

Application-scoped DI is per process. If you configure N server workers, each worker creates and closes its own root
container. Review startup side effects and singleton assumptions before increasing worker count.

The migration test in the repository compares a typical 1.x and 2.0 application and permits changes only in the
startup block; it also executes the 2.0 variant against routes, validation, DI, middleware, and mounts.
