# Миграция с rAPIdy 1.x

Главное правило: **`import rapidy` сохраняется**. Модели, хендлеры, декораторы, middleware, providers и
`HTTPRouter` часто остаются без изменений; ломается транспортный и aiohttp-специфичный слой.

Полный before/after-гайд: [`MIGRATION.md`](https://github.com/rAPIdy-org/rAPIdy/blob/main/MIGRATION.md).

| 1.x | 2.0 |
|---|---|
| `request['key']` | `request.state.key` |
| aiohttp `run_app` options | Uvicorn `workers` / `timeout_graceful_shutdown` |
| aiohttp Gunicorn worker | Uvicorn/Granian/Hypercorn |
| `WebSocketResponse` в `@get` | `@websocket` + `WebSocket` |
| `cleanup_ctx` | `app.lifespan.append(...)` |
| `app.router.*` | decorators / `add_http_router(s)` |
| `app.router.add_static` / ad-hoc tasks | `StaticFiles`, `FileResponse`, `BackgroundTask(s)` |
| `AppKey` | `app.state` / `request.state` |
| `rapidy.mypy` | `rapidy_core.mypy` |
| authentication через middleware/DI | `SecurityConfig`, встроенные схемы, route requirements и guards |

APP-зависимости создаются по одной на процесс worker. Проверьте startup side effects и singleton assumptions перед
увеличением числа workers.

Runtime-аутентификация теперь доступна из `rapidy.security`. Существующие OpenAPI-only `security_schemes` остаются
только документацией, пока не установлен `SecurityConfig`, поэтому переход выполняется явно. После установки
перенесите определения схем и default requirements в `SecurityConfig`: framework будет проверять один контракт для
HTTP и WebSocket и выводить из него OpenAPI metadata.
