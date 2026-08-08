# Быстрый старт

## Установка

После публикации релиза:

```bash
python -m pip install "rapidy[granian]"
```

До публикации `rapidy-core` установите пакеты из монорепозитория:

```bash
python -m pip install -e packages/rapidy_core
python -m pip install -e "packages/rapidy[granian]"
```

## Приложение

Сохраните как `main.py`:

```python
from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.http import Body, get, post


class UserIn(BaseModel):
    name: str
    age: int


@get('/')
async def hello() -> dict[str, str]:
    return {'message': 'Привет, rAPIdy 2.0!'}


@post('/users', status_code=201)
async def create_user(user: UserIn = Body()) -> UserIn:
    return user


app = Rapidy(http_route_handlers=[hello, create_user])
```

Проверяемый исходник находится в [`examples/quickstart.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/quickstart.py).

## Запуск

```bash
granian --interface asgi --host 127.0.0.1 --port 8000 main:app
```

Также можно использовать `uvicorn main:app` или `hypercorn main:app` с соответствующим extra.

```bash
curl http://127.0.0.1:8000/
curl -i -X POST http://127.0.0.1:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada","age":37}'
```

Невалидное значение `age` вернёт HTTP 422 и JSON со списком `errors`.

Далее: [параметры](../guide/parameters.md), [DI](../guide/di.md), [развёртывание](../guide/deployment.md).
