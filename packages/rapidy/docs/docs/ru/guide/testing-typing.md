# Тестирование и типизация

Установите optional testing dependencies и используйте публичный in-process client:

```bash
python -m pip install "rapidy[test]"
```

```python
from rapidy.testing import TestClient

with TestClient(app) as client:
    response = client.get('/')
```

`AsyncTestClient` предоставляет тот же HTTPX request API для async tests. Context manager запускает lifespan и
делает доступными application/request DI, WebSocket и SSE. По умолчанию `raise_server_exceptions=True`, поэтому
неожиданная ошибка handler сразу падает в тест; `False` позволяет проверить сформированный HTTP 500.

```python
async with AsyncTestClient(app) as client:
    async with client.websocket_connect('/ws') as socket:
        await socket.send_json({'message': 'hello'})
        assert await socket.receive_json() == {'message': 'hello'}

    async with client.sse_connect('/events') as events:
        event = await events.receive_event()
        assert event.json() == {'id': 1}
```

У `TestClient` есть синхронные варианты `websocket_connect()` и `sse_connect()`. SSE frames разбираются инкрементально,
а выход из context отключает producer. Живые Granian/Uvicorn нужны для server-specific network/disconnect и graceful
shutdown integration tests.

Test-only Dishka providers передаются через `di_providers`; замена помечается `@provide(..., override=True)`.
Production configuration восстанавливается после context. `create_test_client([handler])` и
`create_async_test_client([handler])` создают компактное приложение для изолированного теста handler.

rAPIdy содержит `py.typed`. Mypy plugin в 2.0 принадлежит core:

```ini
[mypy]
plugins = rapidy_core.mypy
strict = True
```

Пакета `rapidy.mypy` в 2.0 нет. Репозиторий проверяет strict source/usage fixtures, plugin fixture, import parity и
архитектуру на Python 3.13/3.14, а wheel отдельно — на Python 3.12.
