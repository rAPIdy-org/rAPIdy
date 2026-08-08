# Testing and typing

## ASGI tests

An in-process ASGI client keeps framework tests fast and deterministic:

```python
import httpx
import pytest

from main import app


@pytest.mark.asyncio
async def test_hello() -> None:
    async with app.lifespan.ctx_manager():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url='http://testserver',
        ) as client:
            response = await client.get('/')

    assert response.status_code == 200
```

Use real Granian/Uvicorn processes for protocol integration, WebSocket, disconnect, and graceful-shutdown tests. The
rAPIdy repository runs both runtimes in its server acceptance suite.

## Mypy plugin

rAPIdy 2.0 consumes the plugin from `rapidy-core`; `rapidy.mypy` was removed. Configure:

```ini
[mypy]
plugins = rapidy_core.mypy
strict = True
```

or:

```toml
[tool.mypy]
plugins = ["rapidy_core.mypy"]
strict = true
```

The package includes `py.typed`. Handler decorators preserve function types, and `Annotated[T, Body()]` or
`Annotated[T, QueryParam()]` can be used when that style works better for static analysis.

The repository verifies strict framework source, usage fixtures, the plugin fixture, public import parity, and import
architecture on Python 3.13 and 3.14; the built wheel receives a separate Python 3.12 smoke.
