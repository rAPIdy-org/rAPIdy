---
hide:
  - navigation
  - toc
---

<!-- RAPIDY_LEGACY_1X -->

> **⚠️ Историческая документация rAPIdy 1.x.** Страница сохранена только для справки и может описывать aiohttp API, которых нет в rAPIdy 2.0. Для нового кода используйте [актуальную документацию 2.0](https://rapidy.dev/).


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
pip install "rapidy[uvicorn]"
rapidy dev main:app
```

## Возможности 2.0

- Python 3.12+ и только Pydantic v2.
- Нативный ASGI на Granian, Uvicorn или Hypercorn.
- Типизированные Body, Path, Header, Cookie и Query параметры.
- APP-, REQUEST- и WebSocket SESSION-scopes для зависимостей.
- Middleware с извлечением параметров и настройками сериализации ответа.
- Вложенные `HTTPRouter` с общим корневым DI-контейнером.
- WebSocket, SSE и инкрементальный streaming.
- Миграция с сохранением `import rapidy` и удалением aiohttp-специфичного API.

[Начните с quickstart](quickstart/index.md) или перейдите к [параметрам и валидации](guide/parameters.md).
