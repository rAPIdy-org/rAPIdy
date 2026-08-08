# Миграция с rAPIdy 1.x

Главное правило: **`import rapidy` сохраняется**. Модели, хендлеры, декораторы, middleware, providers и
`HTTPRouter` часто остаются без изменений; ломается транспортный и aiohttp-специфичный слой.

Полный before/after-гайд: [`MIGRATION.md`](https://github.com/rAPIdy-org/rAPIdy/blob/main/MIGRATION.md).

| 1.x | 2.0 |
|---|---|
| `request['key']` | `request.state.key` |
| aiohttp `run_app` options | Granian `workers` / `workers_kill_timeout` |
| aiohttp Gunicorn worker | Granian/Uvicorn/Hypercorn |
| `WebSocketResponse` в `@get` | `@websocket` + `WebSocket` |
| `cleanup_ctx` | `app.lifespan.append(...)` |
| `app.router.*` | decorators / `add_http_router(s)` |
| static / BackgroundTasks | внешняя инфраструктура; аналога в 2.0 нет |
| `AppKey` | `app.state` / `request.state` |
| `rapidy.mypy` | `rapidy_core.mypy` |

APP-зависимости создаются по одной на процесс worker. Проверьте startup side effects и singleton assumptions перед
увеличением числа workers.
