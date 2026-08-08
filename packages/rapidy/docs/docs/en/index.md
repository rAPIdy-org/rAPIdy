---
hide:
  - navigation
  - toc
---

<p align="center">
  <img src="../assets/logo-teal.png" alt="rAPIdy" width="440">
</p>

# rAPIdy 2.0

rAPIdy is a typed, async-first ASGI framework powered by Pydantic v2. It provides request and response validation,
dependency injection, middleware, nested routers, WebSockets, Server-Sent Events, and streaming without an aiohttp
runtime dependency.

```python
from rapidy import Rapidy
from rapidy.http import get


@get('/')
async def hello() -> dict[str, str]:
    return {'message': 'Hello, rAPIdy 2.0!'}


app = Rapidy(http_route_handlers=[hello])
```

```bash
pip install "rapidy[granian]"
granian --interface asgi main:app
```

## Highlights

- Python 3.12+ and Pydantic v2 only.
- Native ASGI on Granian, Uvicorn, or Hypercorn.
- Typed body, path, header, cookie, and query parameters.
- Application, request, and WebSocket-session dependency scopes.
- Middleware, nested `HTTPRouter`, WebSockets, SSE, and incremental streaming.
- Migration from 1.x that keeps `import rapidy` while removing aiohttp-specific APIs.

[Start with the quickstart](quickstart/index.md), explore the [guide](guide/parameters.md), or inspect the
[reproducible benchmarks](guide/benchmarks.md).
