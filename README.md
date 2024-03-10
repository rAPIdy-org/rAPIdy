
# rAPIdy 💮
**write quickly** 🚀 **write beautifully** 🌸

<a href="https://github.com/daniil-grois/rAPIdy">rAPIdy<a/>  is an asynchronous web framework built on aiohttp and pydantic, embodying speed and minimalism.

```
pip install rapidy
```

Key Features:
* ✏️ Enhanced code readability and ease of writing
* 📔 Native support for <a href="https://github.com/pydantic/pydantic">pydantic<a/> -> **yes** we fully support **V**1️⃣ and **V**2️⃣❗
* 🚀 Powered by <a href="https://github.com/aio-libs/aiohttp">Aiohttp<a/> with native feature support: Aiohttp, renowned for its speed and productivity, drives our framework
* 📤 Convenient extraction of basic types from incoming data

## Quickstart

rAPIdy seamlessly integrates the foundational capabilities of aiohttp's <a href="https://docs.aiohttp.org/en/stable/web_quickstart.html">quickstart</a>

We offer multiple approaches for defining endpoints in our framework. Explore the following methods:

### RouteTableDef Method:



```python
from rapidy import web
from typing_extensions import Annotated

routes = web.RouteTableDef()


@routes.get('/hello')
async def hello(
        request: web.Request,
        username: Annotated[str, web.JsonBody(min_length=3, max_length=20)],
        password: Annotated[str, web.JsonBody(min_length=8, max_length=40)],
) -> web.Response:
  # Write your code here
  return web.json_response({'username': username, 'password': password})


app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
  web.run_app(app, port=8000)
```

### Using web.<method_name>:

```python
from rapidy import web
from typing_extensions import Annotated


async def hello(
        request: web.Request,
        username: Annotated[str, web.JsonBody(min_length=3, max_length=20)],
        password: Annotated[str, web.JsonBody(min_length=8, max_length=40)],
) -> web.Response:
  # write your code here
  return web.json_response({'username': username, 'password': password})


app = web.Application()
app.add_routes([web.post('/hello', hello)])

if __name__ == '__main__':
  web.run_app(app, port=8000)
```

### Using web.view:

```python
from rapidy import web
from typing_extensions import Annotated


class Handler(web.View):
  async def post(
          self,
          username: Annotated[str, web.JsonBody(min_length=3, max_length=20)],
          password: Annotated[str, web.JsonBody(min_length=8, max_length=40)],
  ) -> web.Response:
    # write your code here
    return web.json_response({'username': username, 'password': password})


app = web.Application()
app.add_routes([web.view('/hello', Handler)])

if __name__ == '__main__':
  web.run_app(app, port=8000)
```

## Pydantic native support

```python
from rapidy import web
from typing_extensions import Annotated


async def hello_handler(
        request: web.Request,
        username: Annotated[str, web.JsonBody(min_length=3, max_length=20)],
        password: Annotated[str, web.JsonBody(min_length=8, max_length=40)],
) -> web.Response:
  # write your code here
  return web.json_response({'username': username, 'password': password})


app = web.Application()
app.add_routes([web.post('/hello', hello_handler)])
web.run_app(app, port=8000)
```
✅✅✅ Success request validation ✅✅✅
```
curl -X POST \
-H "Content-Type: application/json" -d '{"username": "Max", "password": "myAwesomePass"}' -v \
http://127.0.0.1:8000/hello

< HTTP/1.1 200 OK ... {"username": "Max", "password": "myAwesomePass"}
```

❌❌❌ Request validation failure ❌❌❌

```
curl -X POST \
-H "Content-Type: application/json" -d '{"username": "M", "password": "m"}' -v \
http://127.0.0.1:8000/hello

< HTTP/1.1 422 Unprocessable Entity ...
{
    "errors": [
        {
            "loc": ["body", "username"],
            "type": "string_too_short",
            "msg": "String should have at least 3 characters",
            "ctx": {"min_length": 3}
        },
        {
            "type": "string_too_short",
            "loc": ["body", "password"],
            "msg": "String should have at least 8 characters",
            "ctx": {"min_length": 8}
        }
    ]
}

```

## Choose your path

* Unleash your creativity in shaping APIs
* **rAPIdy** supports 3 basic types for defining incoming parameters
  * 🌒 param
    * Path
    * Header
    * Cookie
    * Query
    * BodyJson
    * FormDataBody
    * MultipartBody
  * 🌕 schema
    * PathSchema
    * HeaderSchema
    * CookieSchema
    * QuerySchema
    * BodyJsonSchema
    * FormDataBodySchema
    * MultipartBodySchema
  * 🌑 raw data (no validate with pydantic)
    * PathRaw - **Dict[str, str]**
    * HeaderRaw - **Dict[str, str]**
    * CookieRaw - **Dict[str, str]**
    * QueryRaw - **Dict[str, str]**
    * BodyJsonRaw - **Dict[str, Any]**
    * FormDataBodyRaw - **Dict[str, Any]**
    * MultipartBodyRaw - **Dict[str, Any]**
    * TextBody - **str**
    * BytesBody - **bytes**
    * StreamBody - **aiohttp.streams.StreamReader**

___

\
Explore different ways of defining request attributes in our framework. Below, we provide examples demonstrating the usage of param, schema, and raw data types:

### Defining Request Attributes as Parameters 🌒
```python
from rapidy import web
from typing_extensions import Annotated


async def hello_handler(
        request: web.Request,
        # path params
        path_param: Annotated[str, web.Path],
        # headers
        host: Annotated[str, web.Header(alias='Host')],
        user_agent: Annotated[str, web.Header(alias='User-Agent')],
        # cookie
        user_cookie1: Annotated[str, web.Cookie(alias='UserCookie1')],
        user_cookie2: Annotated[str, web.Cookie(alias='UserCookie2')],
        # query params
        user_param1: Annotated[str, web.Query(alias='UserQueryParam1')],
        user_param2: Annotated[str, web.Cookie(alias='UserQueryParam2')],
        # body
        username: Annotated[str, web.JsonBody(min_length=3, max_length=20)],
        password: Annotated[str, web.JsonBody(min_length=8, max_length=40)],
) -> web.Response:
  # write your code here
  # ...
  return web.Response()


app = web.Application()
app.add_routes([web.post('/hello/{path_param}', hello_handler)])
```
### Defining Request Attributes using Schema 🌕
```python
from pydantic import BaseModel, Field

class PathRequestSchema(BaseModel):
    path_param: str

class HeaderRequestSchema(BaseModel):
    host: str = Field(alias='Host')
    user_agent: str = Field(alias='User-Agent')

class CookieRequestSchema(BaseModel):
    user_cookie1: str = Field(alias='UserCookie1')
    user_cookie2: str = Field(alias='UserCookie2')

class QueryRequestSchema(BaseModel):
    user_cookie1: str = Field(alias='UserQueryParam1')
    user_cookie2: str = Field(alias='UserQueryParam1')

class BodyRequestSchema(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=40)

async def hello_handler(
        request: web.Request,
        path: Annotated[PathRequestSchema, web.PathSchema],
        headers: Annotated[HeaderRequestSchema, web.HeaderSchema],
        cookies: Annotated[CookieRequestSchema, web.Cookie],
        query: Annotated[QueryRequestSchema, web.QuerySchema],
        body: Annotated[BodyRequestSchema, web.JsonBodySchema],
) -> web.Response:

```
### Defining Request Attributes with Raw Data 🌑
```python
async def hello_handler(
        request: web.Request,
        path: Annotated[Dict[str, str], web.PathRaw],
        headers: Annotated[Dict[str, str], web.HeaderRaw],
        cookies: Annotated[Dict[str, str], web.CookieRaw],
        query: Annotated[Dict[str, str], web.QueryRaw],
        body: Annotated[Dict[str, Any], web.JsonBodyRaw],
) -> web.Response:
```
### Combining Different Approaches 🌒 🌕 🌑
```python
async def hello_handler(
        request: web.Request,
        path_param: Annotated[str, web.Path],
        headers: Annotated[Dict[str, str], web.HeaderRaw],
        body: Annotated[BodyRequestSchema, web.JsonBodySchema],
) -> web.Response:
```
