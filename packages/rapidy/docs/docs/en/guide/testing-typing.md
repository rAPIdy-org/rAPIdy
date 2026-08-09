# Testing and typing

## ASGI tests

Install the optional testing dependencies and use the public in-process clients:

```bash
python -m pip install "rapidy[test]"
```

```python
from main import app
from rapidy.testing import TestClient


def test_hello() -> None:
    with TestClient(app) as client:
        response = client.get('/')

    assert response.status_code == 200
```

`AsyncTestClient` provides the same HTTPX request API for async tests. Enter either client as a context manager when
the test needs lifespan, application/request DI, WebSocket, or SSE support. `raise_server_exceptions=True` is the
default, so unexpected handler errors fail the test directly; set it to `False` to assert the rendered HTTP 500.

## WebSocket and SSE

Both protocols run in-process on the client's active lifespan:

```python
async with AsyncTestClient(app) as client:
    async with client.websocket_connect('/ws') as socket:
        await socket.send_json({'message': 'hello'})
        assert await socket.receive_json() == {'message': 'hello'}

    async with client.sse_connect('/events') as events:
        event = await events.receive_event()
        assert event.event == 'created'
        assert event.json() == {'id': 1}
```

`TestClient` exposes synchronous `websocket_connect()` and `sse_connect()` variants. SSE sessions parse frames
incrementally and disconnect the producer when their context exits. Use live Granian/Uvicorn processes only for
server-specific protocol, network disconnect, and graceful-shutdown integration tests.

## Dependency overrides

Pass test-only Dishka providers through `di_providers`. Override declarations use Dishka's explicit
`@provide(..., override=True)` rule. The production provider configuration is restored when the client exits, and
overrides cannot mutate an externally owned container.

`create_test_client([handler])` and `create_async_test_client([handler])` build compact applications for isolated
handler tests. Headers, cookies, redirects, `root_path`, client address, and base URL follow the HTTPX client model.

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
