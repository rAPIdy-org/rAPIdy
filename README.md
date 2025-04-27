<p align="center">
    <a href="https://github.com/daniil-grois/rAPIdy" target="blank">
        <img src="https://rapidy.dev/assets/logo-teal.png" alt="rAPIdy">
    </a>
</p>

<p align="center">
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/v/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2&label=pypi%20rAPIdy" alt="Package version">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/pyversions/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Python versions">
    </a>
    <a href="https://github.com/rAPIdy-org/rAPIdy/actions/workflows/test.yml?query=branch%3Amain" target="blank">
        <img src="https://github.com/rAPIdy-org/rAPIdy/actions/workflows/test.yml/badge.svg?branch=main" alt="license">
    </a>
    <a href="https://github.com/rAPIdy-org/rAPIdy/blob/main/LICENSE" target="blank">
        <img src="https://img.shields.io/badge/license-_MIT-%237e56c2?style=flat" alt="license">
    </a>
    <a href="https://docs.pydantic.dev/latest/" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v1.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V1">
    </a>
    <a href="https://docs.pydantic.dev/latest/" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V2">
    </a>
</p>

<p align="center">
    <i>
        <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a> -
        a fast, lightweight, and modern asynchronous web framework powered by
        <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a>
        and
        <a href="https://github.com/pydantic/pydantic" target="blank">pydantic</a>.
    </i>
</p>

# 🚀 Why rAPIdy?

rAPIdy is designed for developers who need a fast, async-first web framework that combines the performance of aiohttp
with the simplicity and modern features of frameworks like FastAPI.

Simple rAPIdy server:
```python
from rapidy import Rapidy
from rapidy.http import get

@get("/")
async def hello() -> dict[str, str]:
    return {"message": "Hello, rAPIdy!"}

app = Rapidy(http_route_handlers=[hello])
```

## 🔥 Key Features

- Fast & Lightweight – Minimal overhead, built on aiohttp
- Async-First – Fully asynchronous by design
- Built-in Validation – Uses pydantic for request validation
- Simple & Flexible – Supports both rAPIdy-style handler definitions and traditional aiohttp function-based and
class-based routing
- Middleware Support – Easily extend functionality with middleware, including built-in validation for HTTP parameters
(headers, cookies, and body).

---

# 📦 Installation & Setup

Install rAPIdy via pip:
```shell
pip install rapidy
```

---

# 📄 Documentation
Documentation: https://rapidy.dev

---

# 🏁 Quickstart: First Simple Server

Simple rAPIdy server:

_Copy the following code into a file named `main.py`:_
```python
from rapidy import Rapidy
from rapidy.http import get

@get("/")
async def hello() -> dict[str, str]:
    return {"message": "Hello, rAPIdy!"}

rapidy = Rapidy(http_route_handlers=[hello])
```

## Server Startup
There are several ways to start the server:
- Using `run_app`
- Using `WSGI (gunicorn)`

### Using `run_app`
<details open>
<summary>Example:</summary>
Copy the following code to `main.py`:

```python
from rapidy import Rapidy, run_app
from rapidy.http import get

@get("/")
async def hello() -> dict[str, str]:
    return {"message": "Hello, rAPIdy!"}

rapidy = Rapidy(http_route_handlers=[hello])

if __name__ == '__main__':
    run_app(rapidy, host="0.0.0.0", port=8000)
```

Run the server in real-time:
```shell
python3 main.py
```

Your API will be available at http://localhost:8000 🚀
</details>

---

### Using WSGI (gunicorn)
<details>
<summary>Example:</summary>
Gunicorn is a Python WSGI HTTP server for UNIX.

Install gunicorn for your project:
```shell
pip install gunicorn
```

Copy the following code to `main.py`:
```python
from rapidy import Rapidy
from rapidy.http import get

@get("/")
async def hello() -> dict[str, str]:
    return {"message": "Hello, rAPIdy!"}

rapidy = Rapidy(http_route_handlers=[hello])
```

Run the following command in the terminal:
```shell
gunicorn main:rapidy --bind localhost:8000 --reload --worker-class aiohttp.GunicornWebWorker
```

- `main`: Name of the `main.py` file (Python module).
- `rapidy`: Object created inside `main.py` (line: `rapidy = Rapidy()`).
- `--reload`: Restarts the server when code changes are detected. Recommended only for development purposes.

Your API will be available at http://localhost:8000 🚀
</details>

---

# 📌 Advanced Features

## 1️⃣ Routing
Define multiple routes with function-based or class-based views:

_Functional Handlers:_
```python
from rapidy.http import post, Body

@post("/items")
async def create_item(item: dict[str, str] = Body()) -> dict[str, str]:
    return item
```
> [!TIP]
> <details>
>   <summary>Registering without decorators:</summary>
>   <br>
>
>   ```python
>   from rapidy import Rapidy
>   from rapidy.http import post, Body
>
>   async def create_item(item: dict[str, str] = Body()) -> dict[str, str]:
>       return item
>
>   rapidy = Rapidy()
>   rapidy.add_http_routers([post.reg('/items', create_item)])
>   ```
> </details>

_Class-Based Handlers:_

_All methods decorated with @get, @post, etc., are automatically registered as sub-routes._

```python
from rapidy.http import controller, get, post, put, patch, delete, PathParam, Body

@controller('/')
class ItemController:
    @get('/{item_id}')
    async def get_by_id(self, item_id: str = PathParam()) -> dict[str, str]:
        return {'hello': 'rapidy'}

    @get()
    async def get_all(self) -> list[dict[str, str]]:
        return [{'hello': 'rapidy'}, {'hello': 'rapidy'}]

    @post()
    async def post(self, item: dict[str, str] = Body()) -> dict[str, str]:
        return item

    @put()
    async def put(self, item: dict[str, str] = Body()) -> dict[str, str]:
        return item

    @patch()
    async def patch(self, item: dict[str, str] = Body()) -> dict[str, str]:
        return item

    @delete()
    async def delete(self, item: dict[str, str] = Body()) -> dict[str, str]:
        return item
```

> [!TIP]
> <details>
>   <summary>Registering without decorators:</summary>
>   <br>
>
> ```python
> from rapidy import Rapidy
> from rapidy.http import PathParam, get, post, put, patch, delete, controller, Body
>
> class ItemController:
>     @get('/{item_id}')
>     async def get_by_id(self, item_id: str = PathParam()) -> dict[str, str]:
>         return {'hello': 'rapidy'}
>
>     @get()
>     async def get_all(self) -> list[dict[str, str]]:
>         return [{'hello': 'rapidy'}, {'hello': 'rapidy'}]
>
>     @post()
>     async def post(self, item: dict[str, str] = Body()) -> dict[str, str]:
>         return item
>
>     @put()
>     async def put(self, item: dict[str, str] = Body()) -> dict[str, str]:
>         return item
>
>     @patch()
>     async def patch(self, item: dict[str, str] = Body()) -> dict[str, str]:
>         return item
>
>     @delete()
>     async def delete(self, item: dict[str, str] = Body()) -> dict[str, str]:
>         return item
>
> rapidy = Rapidy(
>     http_route_handlers=[controller.reg('/', ItemController)],
> )
> ```
> You can register a `controller` in a router without a decorator, but the methods still need to be wrapped with decorators.
> </details>

## 2️⃣ Request Validation
rAPIdy uses pydantic not only to validate request data but also for response data serialization.
This ensures data consistency and type safety throughout the entire request-response cycle:

```python
from rapidy.http import post, Body
from pydantic import BaseModel

class ItemSchema(BaseModel):
    name: str
    price: float

@post("/items")
async def create_item(data: ItemSchema = Body()) -> ItemSchema:
    return data
```

_If validation fails, a 422 Unprocessable Entity response with error details is automatically returned._

> [!TIP]
> <details>
>   <summary>Example:</summary>
>   <br>
>
>   ```python
>   from pydantic import BaseModel, Field
>   from rapidy import Rapidy
>   from rapidy.http import PathParam, Body, Request, Header, StreamResponse, middleware, post
>   from rapidy.typedefs import CallNext
>
>   TOKEN_REGEXP = '^[Bb]earer (?P<token>[A-Za-z0-9-_=]*)'
>
>   class RequestBody(BaseModel):
>       username: str = Field(min_length=2, max_length=50)
>       password: str = Field(min_length=2, max_length=50)
>
>   class ResponseBody(BaseModel):
>       hello: str = 'rapidy'
>
>   @middleware
>   async def get_bearer_middleware(
>           request: Request,
>           call_next: CallNext,
>           bearer_token: str = Header(alias='Authorization', pattern=TOKEN_REGEXP),
>   ) -> StreamResponse:
>       # process token here ...
>       return await call_next(request)
>
>   @post('/{user_id}')
>   async def handler(
>           user_id: str = PathParam(),
>           body: RequestBody = Body(),
>   ) -> str:
>       return 'success'
>
>   app = Rapidy(
>       middlewares=[get_bearer_middleware],
>       http_route_handlers=[handler],
>   )
>   ```
>   _Successful Request Validation_:
>   ```shell
>   curl -X POST \
>   -H "Content-Type: application/json" \
>   -H "Authorization: Bearer my-token" \
>   -d '{"username": "Username", "password": "Password"}' \
>   -v http://127.0.0.1:8080/1
>   ```
>   ```text
>   < HTTP/1.1 200 OK ...
>   success
>   ```
>
>   _Failed Request Validation_:
>   ```shell
>   curl -X POST \
>   -H "Content-Type: application/json" \
>   -H "Authorization: Bearer my-token" \
>   -d '{"username": "U", "password": "P"}' \
>   -v http://127.0.0.1:8080/1
>   ```
>   ```text
>   < HTTP/1.1 422 Unprocessable Entity ...
>   {
>       "errors": [
>           {
>               "type": "string_too_short",
>               "loc": ["body", "username"],
>               "msg": "String should have at least 2 characters",
>               "ctx": {"min_length": 2}
>           },
>           {
>               "type": "string_too_short",
>               "loc": ["body", "password"],
>               "msg": "String should have at least 2 characters",
>               "ctx": {"min_length": 2}
>           }
>       ]
>   }
>   ```
> </details>

## 3️⃣ Middleware Support
Easily add powerful middleware for authentication, logging, and more. rAPIdy allows you to validate HTTP parameters
(headers, cookies, body) directly within middleware for enhanced flexibility:

_Middleware can be used for authentication, logging, or other cross-cutting concerns._

```python
from rapidy import Rapidy
from rapidy.http import PathParam, Request, Header, StreamResponse, middleware, post
from rapidy.typedefs import CallNext

TOKEN_REGEXP = '^[Bb]earer (?P<token>[A-Za-z0-9-_=]*)'

@middleware
async def get_bearer_middleware(
        request: Request,
        call_next: CallNext,
        bearer_token: str = Header(alias='Authorization', pattern=TOKEN_REGEXP),
) -> StreamResponse:
    # process token here ...
    return await call_next(request)

@post('/{user_id}')
async def handler(user_id: str = PathParam()) -> str:
    return 'success'

app = Rapidy(
    middlewares=[get_bearer_middleware],
    http_route_handlers=[handler],
)
```

> [!NOTE]
> Middleware functions must always take `Request` as the first argument and `call_next` as the second argument.

---

## 4️⃣ Dependency Injection

`Rapidy` uses the [dishka](https://dishka.readthedocs.io/en/stable/) library as its built-in Dependency Injection (DI) mechanism.

We aimed to choose a DI library aligned with the philosophy of `Rapidy`: simplicity, speed, transparency, and scalability.
`dishka` perfectly fits these principles, offering developers a powerful tool without unnecessary complexity.

In `Rapidy`, dishka is available out-of-the-box — no additional setup required.

```python
from rapidy import Rapidy
from rapidy.http import Request, StreamResponse, get, middleware
from rapidy.typedefs import CallNext
from rapidy.depends import provide, Provider, Scope, FromDI

class FooProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def some_obj(self) -> int:
        return 1

@middleware
async def some_middleware(
    request: Request,
    call_next: CallNext,
    some_obj: FromDI[int],
) -> StreamResponse:
    print({"value": some_obj})
    return await call_next(request)

@get('/')
async def handler(some_obj: FromDI[int]) -> dict:
    return {"value": some_obj}

app = Rapidy(
    middlewares=[some_middleware],
    http_route_handlers=[handler],
    di_providers=[FooProvider()],
)
```

To gain a deeper understanding of how the DI mechanism works, refer to the documentation for [Rapidy](https://rapidy.dev) and [dishka](https://dishka.readthedocs.io/en/stable/).

---

## 5️⃣ Lifespan Support
Lifespan is a lifecycle manager for background tasks within Rapidy.

_Although aiohttp supports the background tasks feature, rapidy does it more conveniently._

Lifespan manages tasks that should be started: before or after server startup, or should always run.

There are several ways to start tasks: `on_startup`, `on_shutdown`, `on_cleanup`, `lifespan`.

---

### on_startup
`on_startup` - tasks that will be executed in the event loop along with the application's request handlers immediately
after the application starts.

```python
from rapidy import Rapidy

def startup() -> None:
    print('startup')

rapidy = Rapidy(on_startup=[startup])
```

<details>
<summary>Additional examples:</summary>

```python
from rapidy import Rapidy

def startup(rapidy: Rapidy) -> None:
    print(f'startup, application: {rapidy}')

rapidy = Rapidy(on_startup=[startup])
```
```python
from rapidy import Rapidy

async def async_startup() -> None:
    print('async_startup')

rapidy = Rapidy(on_startup=[async_startup])
```
```python
from rapidy import Rapidy

async def async_startup(rapidy: Rapidy) -> None:
    print(f'async_startup, application: {rapidy}')

rapidy = Rapidy(on_startup=[async_startup])
```
</details>

_Adding `on_startup` to an already created `Application` object._
```python
rapidy = Rapidy()
rapidy.lifespan.on_startup.append(startup)
```

---

### on_shutdown
`on_shutdown` - tasks that will be executed after the server stops.

```python
from rapidy import Rapidy

def shutdown() -> None:
    print('shutdown')

rapidy = Rapidy(on_shutdown=[shutdown])
```

<details>
<summary>Additional examples:</summary>

```python
from rapidy import Rapidy

def shutdown(rapidy: Rapidy) -> None:
    print(f'shutdown, application: {rapidy}')

rapidy = Rapidy(on_shutdown=[shutdown])
```
```python
from rapidy import Rapidy

async def async_shutdown() -> None:
    print('async_shutdown')

rapidy = Rapidy(on_shutdown=[async_shutdown])
```
```python
from rapidy import Rapidy

async def async_shutdown(rapidy: Rapidy) -> None:
    print(f'async_shutdown, application: {rapidy}')

rapidy = Rapidy(on_shutdown=[async_shutdown])
```
</details>

_Adding `on_shutdown` to an already created `Application` object._
```python
rapidy = Rapidy()
rapidy.lifespan.on_shutdown.append(shutdown)
```

---

### on_cleanup
`on_cleanup` - tasks that will be executed after the server stops and all `on_shutdown` tasks are completed.

```python
from rapidy import Rapidy

def cleanup() -> None:
    print('cleanup')

rapidy = Rapidy(on_cleanup=[cleanup])
```

<details>
<summary>Additional examples:</summary>

```python
from rapidy import Rapidy

def cleanup(rapidy: Rapidy) -> None:
    print(f'cleanup, application: {rapidy}')

rapidy = Rapidy(on_cleanup=[cleanup])
```
```python
from rapidy import Rapidy

async def async_cleanup() -> None:
    print('async_cleanup')

rapidy = Rapidy(on_cleanup=[async_cleanup])
```
```python
from rapidy import Rapidy

async def async_cleanup(rapidy: Rapidy) -> None:
    print(f'async_cleanup, application: {rapidy}')

rapidy = Rapidy(on_cleanup=[async_cleanup])
```
</details>

_Adding `on_cleanup` to an already created `Application` object._
```python
rapidy = Rapidy()
rapidy.lifespan.on_cleanup.append(cleanup)
```

---

### lifespan
`lifespan` - manages background tasks.

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from rapidy import Rapidy

@asynccontextmanager
async def bg_task() -> AsyncGenerator[None, None]:
    try:
        print('starting background task')
        yield
    finally:
        print('finishing background task')

rapidy = Rapidy(
    lifespan=[bg_task()],
)
```

<details>
<summary>Additional example:</summary>

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from rapidy import Rapidy

@asynccontextmanager
async def bg_task_with_app(rapidy: Rapidy) -> AsyncGenerator[None, None]:
    try:
        print('starting background task')
        yield
    finally:
        print('finishing background task')

rapidy = Rapidy(
    lifespan=[bg_task_with_app],
)
```
</details>

_Adding `lifespan` to an already created `Application` object._
```python
rapidy = Rapidy()
rapidy.lifespan.append(bg_task())
```

# 🧪 Testing with rAPIdy
You can use `pytest` and `pytest-aiohttp` for testing your rAPIdy application:

_Install pytest and pytest-aiohttp_
```shell
pip install pytest pytest-aiohttp
```

Example of a simple test:
```python
from rapidy import Rapidy
from rapidy.http import get
from pytest_aiohttp.plugin import AiohttpClient

@get('/')
async def hello() -> dict[str, str]:
    return {'message': 'Hello, rAPIdy!'}

async def test_hello(aiohttp_client: AiohttpClient) -> None:
    app = Rapidy(http_route_handlers=[hello])

    client = await aiohttp_client(app)

    resp = await client.get('/')
    assert resp.status == 200
    assert await resp.json() == {'message': 'Hello, rAPIdy!'}
```



# 🔄 Migration from aiohttp
rAPIdy is built on top of aiohttp, offering a familiar development experience with powerful enhancements:

- Full Compatibility with aiohttp Syntax – rAPIdy fully supports the definition of HTTP handlers just like in aiohttp,
offering the same capabilities. For more details, refer to the rAPIdy documentation.
- Cleaner Routing Syntax – No need for web.RouteTableDef, making route definitions more concise and readable.
- Significantly Reduced Boilerplate Code – rAPIdy minimizes the amount of code required compared to aiohttp,
allowing developers to focus on business logic rather than repetitive setup.
- Built-in Request Validation and Response Serialization – Powered by pydantic, rAPIdy automatically validates incoming
requests and serializes responses, ensuring data consistency and reducing potential errors.
- Powerful Middlewares – First-class support for middleware and easy-to-use dependency injection out of
the box.
- Lifespan support.

---

# 🛠️ Mypy Support
`rAPIdy` includes its own plugin for <a href="https://mypy.readthedocs.io/en/stable/getting_started.html" target="blank">mypy</a>.

_The rapidy.mypy plugin helps with type checking in code that uses rAPIdy._

Add the auxiliary configuration to your mypy configuration file.

_mypy.ini_
```ini
; Example configuration for mypy.ini
; ...
[tool.mypy]
plugins =
    pydantic.mypy
    rapidy.mypy
; ...
```

_pyproject.toml_
```toml
# Example configuration for pyproject.toml
# ...
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"
]
# ...
```

---

# 🛤️ Roadmap

We're actively improving rAPIdy to make it more powerful and efficient. Stay up-to-date with our latest milestones and
future plans by checking out the detailed roadmap below.

You can find the full and detailed roadmap on our GitHub page:
[ROADMAP.md](https://github.com/daniil-grois/rAPIdy/blob/main/ROADMAP.md)

---

# 🤝 Contributing & Support
Want to improve rAPIdy? We welcome contributions! 🚀
- Report Issues: [GitHub Issues](https://github.com/daniil-grois/rAPIdy/issues)
- Pull Requests: Fork & create PRs!
- Contribution Guide: [CONTRIBUTING.md](https://github.com/daniil-grois/rAPIdy/blob/main/CONTRIBUTING.md)

---

# 📜 License
rAPIdy is licensed under the MIT License. See LICENSE for details.

---

Start building fast, reliable, and modern APIs with rAPIdy today! 🚀
