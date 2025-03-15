# Testing

## Description
`Rapidy` is tested in the same way as `aiohttp`.

To get started, install the testing plugin:
```shell
pip install pytest-aiohttp
```

!!! note ""
    You can learn more about testing `aiohttp`
    **<a href="https://docs.aiohttp.org/en/stable/testing.html" target="_blank">here</a>**.

## Example test for a simple application

### Project structure
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
Contents of `app/main.py`:
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
Contents of `tests/conftest.py`:
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
Contents of `tests/test_hello.py`:
```python
from aiohttp.test_utils import TestClient

async def test_hello(app_client: TestClient) -> None:
    response = await app_client.get('/')
    text = await response.text()

    assert response.status == 200
    assert 'Hello, world' == text
```

##### pytest.ini
Contents of `tests/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

### Running tests
#### Simple test execution
To run your tests using `pytest`, execute the command below:
```shell
pytest ./tests
```

!!! tip "You can learn more about `pytest` **<a href="https://docs.pytest.org/en/stable/" target="_blank">here</a>**"

#### Running tests with coverage
To run tests in `pytest` with code coverage, first install the `pytest-cov` plugin:
```shell
pip install pytest-cov
```

Running tests with coverage output in the console:
```shell
pytest --cov=app --cov-report=term-missing
```

Running tests with an HTML coverage report:
```shell
pytest --cov=app --cov-report=html
```
