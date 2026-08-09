# Быстрый старт

## Установка

После публикации релиза:

```bash
python -m pip install "rapidy[uvicorn]"
```

`pip install rapidy` устанавливает framework без ASGI-сервера. Extra Uvicorn включает встроенные команды
`rapidy run` и `rapidy dev`.

До публикации `rapidy-core` установите пакеты из монорепозитория:

```bash
python -m pip install -e packages/rapidy_core
python -m pip install -e "packages/rapidy[uvicorn]"
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
rapidy dev main:app
```

Команда использует Uvicorn из выбранного extra. Granian и Hypercorn доступны через собственные extras и не
устанавливают Uvicorn.

```bash
curl http://127.0.0.1:8080/
curl -i -X POST http://127.0.0.1:8080/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada","age":37}'
```

Невалидное значение `age` вернёт HTTP 422 и JSON со списком `errors`.

Далее: [параметры](../guide/parameters.md), [DI](../guide/di.md), [развёртывание](../guide/deployment.md).
