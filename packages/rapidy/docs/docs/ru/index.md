---
hide:
  - navigation
  - toc
---

<p align="center">
  <img src="../assets/logo-teal.png" alt="rAPIdy" width="440">
</p>

# rAPIdy 2.0

rAPIdy — типизированный асинхронный ASGI-фреймворк на Pydantic v2. Он предоставляет валидацию запросов и ответов,
DI, middleware, вложенные роутеры, WebSocket, Server-Sent Events и streaming без runtime-зависимости от aiohttp.

```python
from rapidy import Rapidy
from rapidy.http import get


@get('/')
async def hello() -> dict[str, str]:
    return {'message': 'Привет, rAPIdy 2.0!'}


app = Rapidy(http_route_handlers=[hello])
```

```bash
pip install "rapidy[granian]"
granian --interface asgi main:app
```

## Основные возможности

- Python 3.12+ и только Pydantic v2.
- Нативный ASGI на Granian, Uvicorn или Hypercorn.
- Типизированные Body, Path, Header, Cookie и Query параметры.
- APP-, REQUEST- и WebSocket SESSION-scopes для зависимостей.
- Middleware, вложенные `HTTPRouter`, WebSocket, SSE и streaming.
- Именованные reverse routes, RFC 9457 errors, structured access logs и опциональный OpenTelemetry.
- Миграция с сохранением `import rapidy` и удалением aiohttp-специфичного API.

[Быстрый старт](quickstart/index.md) · [руководство](guide/parameters.md) · [бенчмарки](guide/benchmarks.md)
