<p align="center">
    <a href="https://github.com/daniil-grois/rAPIdy" target="blank">
        <img src="docs/assets/logo-teal.png" alt="rAPIdy">
    </a>
</p>

<p align="center">
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/dm/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Package downloads">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/v/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2&label=pypi%20rAPIdy" alt="Package version">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/pyversions/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Python versions">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v1.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V1">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V2">
    </a>
</p>

<p align="center">
    <i>
        <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a>
        is a minimalist web framework designed for developers who value speed and convenience.<br/>
        Built on top of <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a> and <a href="https://github.com/pydantic/pydantic" target="blank">pydantic</a>,
        it enables you to fully utilize the strengths of this stack.
    </i>
</p>

# Key Features
* ✏️ **Minimalism**: Access and validate data effortlessly in just one line of code.
* 🐍 **Native Python Support**: Ensures seamless compatibility with native Python types.
* 📔 **Pydantic Integration**: Leverages <a href="https://github.com/pydantic/pydantic">pydantic</a> for powerful and reliable data validation.
* 🚀 **Powered by aiohttp**: Utilizes <a href="https://github.com/aio-libs/aiohttp">aiohttp</a> for robust asynchronous functionality.
* 📤 **Efficient Data Handling**: Simplifies the extraction of basic data types from incoming requests in Python.

---
# Documentation
> [!TIP]
> **Mkdocs Coming Soon:** Now # TODO: link

---
# Installation
> [!NOTE]
> ```bash
> pip install rapidy
> ```

---

# Server
## Quickstart
> [!NOTE]
> rAPIdy is built on aiohttp and supports all handler definition methods.

### HTTP Handlers
> [!NOTE]
> `rAPIdy` allows you to define handlers in the same way as in <a href="https://docs.aiohttp.org/en/stable/web_quickstart.html" target="blank">aiohttp-quickstart</a>.

#### Functional Handlers
```python
from rapidy import Rapidy
from rapidy.http import post

@post('/')
async def handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.add_http_router(handler)
```

> [!TIP]
> <details>
>   <summary>Registering without decorators</summary>
>   <br>
>
>   ```python
>   from rapidy import Rapidy
>   from rapidy.http import post
>
>   async def handler() -> dict[str, str]:
>       return {'hello': 'rapidy'}
>
>   rapidy = Rapidy()
>   rapidy.add_http_router(post.handler('/', handler))
>   ```
> </details>

---

#### Class-Based Handlers
```python
from rapidy import Rapidy
from rapidy.http import View, view, PathParam, get

@view('/')
class Handler(View):
    @get('/{user_id}')
    async def get(self, user_id: str = PathParam()) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def post(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def put(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def patch(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def delete(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

rapidy = Rapidy()
rapidy.add_http_router(Handler)
```

> [!TIP]
> <details>
>   <summary>Registering without decorators</summary>
>   <br>
>
> ```python
> from rapidy import Rapidy
> from rapidy.http import get, view, View, PathParam
>
> class Handler(View):
>     async def get(self, user_id: str = PathParam()) -> dict[str, str]:
>         return {'hello': 'rapidy'}
>
>     async def post(self) -> dict[str, str]:
>         return {'hello': 'rapidy'}
>
>     async def put(self) -> dict[str, str]:
>         return {'hello': 'rapidy'}
>
>     async def patch(self) -> dict[str, str]:
>         return {'hello': 'rapidy'}
>
>     async def delete(self) -> dict[str, str]:
>         return {'hello': 'rapidy'}
>
> rapidy = Rapidy()
> rapidy.add_http_router(get.handler('/{user_id}', Handler))
> rapidy.add_http_router(view.handler('/', Handler))
> ```
> </details>

---

#### Middleware
```python
from rapidy import Rapidy
from rapidy.http import Request, StreamResponse, get, middleware
from rapidy.typedefs import CallNext

@middleware
async def hello_middleware(request: Request, call_next: CallNext) -> StreamResponse:
    request['data'] = {'hello': 'rapidy'}
    return await call_next(request)

@get('/')
async def handler(request: Request) -> dict[str, str]:
    return request['data']

rapidy = Rapidy(middlewares=[hello_middleware])
rapidy.add_http_router(handler)
```

> [!WARNING]
> Middleware functions must always take `Request` as the first argument and `call_next` as the second argument.

---

#### HTTPRoute
##### Registering Functional Handlers
```python
from rapidy import Rapidy
from rapidy.http import post, HTTPRouter

@post('/hello')
async def hello_handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

@post('/hi')
async def hi_handler() -> dict[str, str]:
    return {'hi': 'rapidy'}

api_router = HTTPRouter('/api', [hello_handler])

rapidy = Rapidy()
rapidy.add_http_routers([api_router, hi_handler])
```

> [!TIP]
> <details>
>   <summary>Registering functional handlers without decorators</summary>
>   <br>
>
>   ```python
>   from rapidy import Rapidy
>   from rapidy.http import post, HTTPRouter
>
>   async def hello_handler() -> dict[str, str]:
>       return {'hello': 'rapidy'}
>
>   async def hi_handler() -> dict[str, str]:
>       return {'hi': 'rapidy'}
>
>   api_router = HTTPRouter('/api', [post.handler('/hello', hello_handler)])
>
>   rapidy = Rapidy()
>   rapidy.add_http_routers([api_router, post.handler('/hi', hi_handler)])
>   ```
> </details>

---

##### Registering Class-Based Handlers
```python
from rapidy import Rapidy
from rapidy.http import View, view, HTTPRouter

@view('/hello_view')
class Handler(View):
    async def get(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def post(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def put(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def patch(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

    async def delete(self) -> dict[str, str]:
        return {'hello': 'rapidy'}

api_router = HTTPRouter('/api', [Handler])

rapidy = Rapidy()
rapidy.add_http_router(api_router)
```

> [!TIP]
> <details>
>   <summary>Registering class-based handlers without decorators</summary>
>   <br>
>
>   ```python
>   from rapidy import Rapidy
>   from rapidy.http import View, view, HTTPRouter
>
>   class Handler(View):
>       async def get(self) -> dict[str, str]:
>           return {'hello': 'rapidy'}
>
>       async def post(self) -> dict[str, str]:
>           return {'hello': 'rapidy'}
>
>       async def put(self) -> dict[str, str]:
>           return {'hello': 'rapidy'}
>
>       async def patch(self) -> dict[str, str]:
>           return {'hello': 'rapidy'}
>
>       async def delete(self) -> dict[str, str]:
>           return {'hello': 'rapidy'}
>
>   api_router = HTTPRouter('/api', [view.handler('/hello_view', Handler)])
>
>   rapidy = Rapidy()
>   rapidy.add_http_router(api_router)
>   ```
> </details>

---

## HTTP Request Validation
```python
from pydantic import BaseModel, Field
from rapidy import Rapidy, run_app
from rapidy.http import PathParam, Body, Request, Header, StreamResponse, middleware, post
from rapidy.typedefs import CallNext

TOKEN_REGEXP = '^[Bb]earer (?P<token>[A-Za-z0-9-_=]*)'

class RequestBody(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=2, max_length=50)

class ResponseBody(BaseModel):
    hello: str = 'rapidy'

