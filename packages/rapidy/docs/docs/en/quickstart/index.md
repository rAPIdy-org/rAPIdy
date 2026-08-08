# Quickstart

## Install

For a published release:

```bash
python -m pip install "rapidy[granian]"
```

When working from the monorepo before `rapidy-core` is published:

```bash
python -m pip install -e packages/rapidy_core
python -m pip install -e "packages/rapidy[granian]"
```

## Create an application

Save this as `main.py`:

```python
from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.http import Body, get, post


class UserIn(BaseModel):
    name: str
    age: int


class UserOut(UserIn):
    id: int


@get('/')
async def hello() -> dict[str, str]:
    return {'message': 'Hello, rAPIdy 2.0!'}


@post('/users', status_code=201)
async def create_user(user: UserIn = Body()) -> UserOut:
    return UserOut(id=1, **user.model_dump())


app = Rapidy(http_route_handlers=[hello, create_user])
```

The checked and tested source is [`examples/quickstart.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/quickstart.py).

## Run it

```bash
granian --interface asgi --host 127.0.0.1 --port 8000 main:app
```

You may instead use `uvicorn main:app` or `hypercorn main:app` after installing the corresponding extra.

```bash
curl http://127.0.0.1:8000/
curl -i -X POST http://127.0.0.1:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada","age":37}'
```

The second response has status 201. An invalid age produces HTTP 422 and a JSON `errors` list.

## Use a Python entry point

`run_app` uses Granian's programmatic API:

```python
from rapidy import run_app

if __name__ == '__main__':
    run_app(app, host='127.0.0.1', port=8000, workers=1)
```

Continue with [request parameters](../guide/parameters.md), [dependency injection](../guide/di.md), or
[deployment](../guide/deployment.md).
