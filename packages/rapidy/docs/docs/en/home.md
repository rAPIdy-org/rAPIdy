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
pip install "rapidy[uvicorn]"
rapidy dev main:app
```

## What 2.0 provides

- Python 3.12+ and Pydantic v2 only.
- Native ASGI on Granian, Uvicorn, or Hypercorn.
- Typed request sources: body, path, header, cookie, and query.
- Application, request, and WebSocket-session dependency scopes.
- Middleware with parameter extraction and response serialization options.
- Nested `HTTPRouter` mounts with shared root DI.
- Native WebSockets, SSE, and incremental streaming.
- A migration path that keeps `import rapidy` while removing aiohttp-specific APIs.

[Start with the quickstart](quickstart/index.md) or go directly to [parameters and validation](guide/parameters.md).

The benchmark report is deliberately numerical and includes regressions as well as wins. See
[methodology and raw results](guide/benchmarks.md).
