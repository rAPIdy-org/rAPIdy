# Testing

## Описание
`Rapidy` тестируется точно так же, как и `aiohttp`.

Для начала установите плагин для тестирования:
```shell
pip install pytest-aiohttp
```

!!! note ""
    Подробнее о тестировании `aiohttp` можно ознакомиться
    **<a href="https://docs.aiohttp.org/en/stable/testing.html" target="_blank">здесь</a>**.

## Пример теста простого приложения

### Структура проекта
```shell
├── app
│   ├── __init__.py
│   └── main.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── pytest.ini
    └── test_hello.py
```

#### app
##### main.py
Содержимое файла `app/main.py`:
```python
from rapidy import Rapidy, run_app
from rapidy.http import get

@get('/')
async def hello() -> str:
    return 'Hello, world'

def create_app() -> Rapidy:
    app = Rapidy(
        http_route_handlers=[hello],
    )

    # add additional app creation logic ...

    return app

if __name__ == '__main__':
    app = create_app()
    run_app(app, host='0.0.0.0', port=8080)
```

#### tests
##### conftest.py
Содержимое файла `tests/conftest.py`:
```python
import pytest

from rapidy import Rapidy
from typing import AsyncGenerator
from aiohttp.test_utils import TestClient, TestServer, BaseTestServer

from app.main import create_app

@pytest.fixture(scope='session')
async def app() -> Rapidy:
    return create_app()

@pytest.fixture
async def app_server(app: Rapidy) -> AsyncGenerator[BaseTestServer, None]:
    async with TestServer(app) as server:
        yield server

@pytest.fixture
async def app_client(app_server: BaseTestServer) -> AsyncGenerator[TestClient, None]:
    async with TestClient(app_server) as client:
        yield client
```

##### test_hello.py
Содержимое файла `tests/test_hello.py`:
```python
from aiohttp.test_utils import TestClient

async def test_hello(app_client: TestClient) -> None:
    response = await app_client.get('/')
    text = await response.text()

    assert response.status == 200
    assert 'Hello, world' == text
```

##### pytest.ini
Содержимое файла `tests/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

### Запуск теста
#### Простой запуск теста
Чтобы запустить ваши тесты с помощью `pytest` выполните команду ниже:
```shell
pytest ./tests
```

!!! tip "Подробнее о `pytest` можно прочитать **<a href="https://docs.pytest.org/en/stable/" target="_blank">здесь</a>**"

#### Запуск теста с покрытием
Чтобы запустить тесты в pytest с покрытием кода, вначале установите плагин `pytest-cov`.
```shell
pip install pytest-cov
```

Запуск теста с выводом покрытия в консоль:
```shell
pytest --cov=app --cov-report=term-missing
```

Запуск теста с формированием HTML-отчета:
```shell
pytest --cov=app --cov-report=html
```
