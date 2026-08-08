# Тестирование и типизация

Для быстрых unit/integration тестов используйте ASGI transport:

```python
import httpx

async with app.lifespan.ctx_manager():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://testserver',
    ) as client:
        response = await client.get('/')
```

WebSocket, disconnect и graceful shutdown дополнительно проверяйте на живом Granian/Uvicorn.

rAPIdy содержит `py.typed`. Mypy plugin в 2.0 принадлежит core:

```ini
[mypy]
plugins = rapidy_core.mypy
strict = True
```

Пакета `rapidy.mypy` в 2.0 нет. Репозиторий проверяет strict source/usage fixtures, plugin fixture, import parity и
архитектуру на Python 3.13/3.14, а wheel отдельно — на Python 3.12.
