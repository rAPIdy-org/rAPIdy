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
        - is a minimalist web framework for those who prioritize speed and convenience.<br/>
        Built upon <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a> and <a href="https://github.com/pydantic/pydantic" target="blank">pydantic</a>,
        allowing you to fully leverage the advantages of this stack.
    </i>
</p>


# Key features

* ✏️ **Minimalism**: Retrieve and check data effortlessly using just a single line of code
* 🐍 **Native Python Support**: Offers seamless compatibility with Python native types
* 📔 **Pydantic Integration**: Fully integrated with <a href="https://github.com/pydantic/pydantic">pydantic</a> for robust data validation
* 🚀 **Powered by aiohttp**: Utilizes <a href="https://github.com/aio-libs/aiohttp">aiohttp</a> to leverage its powerful asynchronous features
* 📤 **Efficient Data Handling**: Simplifies the extraction of basic types from incoming data in Python


---
# Documentation
> [!TIP]
> Coming soon: 2024.06
---


# Installation
> [!NOTE]
> ```bash
> pip install rapidy
> ```
---

# Server
## Quickstart
### Handlers
```python
from rapidy import web

routes = web.RouteTableDef()

@routes.post('/')
async def handler(
        auth_token: str = web.Header(alias='Authorization'),
        username: str = web.JsonBody(),
        password: str = web.JsonBody(min_length=8),
) -> web.Response:
    print({'auth_token': auth_token, 'username': username, 'password': password})
    return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

> [!NOTE]
> `rAPIdy` allows you to define handlers just like in <a href="https://docs.aiohttp.org/en/stable/web_quickstart.html" target="blank">aiohttp-quickstart</a>,
> but with a key improvement:
> the `request` parameter is no longer required for functional handlers
>
> If you need to access the current `request` within a handler,
> simply declare an attribute with any name of your choosing and specify its type as `web.Request`. rAPIdy will automatically replace this attribute with the current instance of `web.Request`.
```python
from typing import Annotated
from rapidy import web

routes = web.RouteTableDef()

@routes.get('/default_handler_example')
async def default_handler_example(
        request: str = web.Request,
) -> web.Response:
    print({'request': request})
    return web.json_response({'data': 'success'})

@routes.get('/handler_without_request_example')
async def handler_without_request_example() -> web.Response:
    return web.json_response({'data': 'success'})

@routes.get('/handler_request_as_snd_attr_example')
async def handler_request_as_snd_attr_example(
        host: Annotated[str, web.Header(alias='Host')],
        request: web.Request,
) -> web.Response:
    print({'host': host, 'request': request})
    return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
   web.run_app(app, host='127.0.0.1', port=8080)
```

### Middlewares
Processing an Authorization Token in Middleware

```python
from rapidy import web
from rapidy.typedefs import HandlerType

@web.middleware
async def hello_middleware(
        request: web.Request,
        handler: HandlerType,
        bearer_token: str = web.Header(alias='Authorization'),
) -> web.StreamResponse:
    request['token'] = bearer_token
    return await handler(request)

async def handler(
        request: web.Request,
        host: str = web.Header(alias='Host'),
        username: str = web.JsonBody(),
) -> web.Response:
    example_data = {'token': request['token'], 'host': host, 'username': username}
    return web.json_response(example_data)

app = web.Application(middlewares=[hello_middleware])
app.add_routes([web.post('/', handler)])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

> [!IMPORTANT]
> The first two attributes in a middleware are mandatory and must always represent the `request` and the `handler` respectively. These attributes are essential for the correct functioning of the middleware
---

## Request validation
`rAPIdy` utilizes custom parameters to validate incoming HTTP request data, ensuring integrity and compliance with expected formats

> [!TIP]
> A parameter in `rAPIdy` represents an object that mcontains meta-information about the type of data it retrieves

A parameter in `rAPIdy` offers all the functionalities of `pydantic.Field`, and even more. This means `rAPIdy-parameter` support every type of validation that `pydantic` provides, ensuring comprehensive data integrity and conformity

```python
from decimal import Decimal
from pydantic import BaseModel, Field
from rapidy import web

routes = web.RouteTableDef()

class Schema(BaseModel):
    positive: int = Field(gt=0)
    non_negative: int = Field(ge=0)
    negative: int = Field(lt=0)
    non_positive: int = Field(le=0)
    even: int = Field(multiple_of=2)
    love_for_pydantic: float = Field(allow_inf_nan=True)
    short: str = Field(min_length=3)
    long: str = Field(max_length=10)
    regex: str = Field(pattern=r'^\d*$')
    precise: Decimal = Field(max_digits=5, decimal_places=2)

@routes.get('/')
async def handler(
    positive: int = web.JsonBody(gt=0),
    non_negative: int = web.JsonBody(ge=0),
    negative: int = web.JsonBody(lt=0),
    non_positive: int = web.JsonBody(le=0),
    even: int = web.JsonBody(multiple_of=2),
    love_for_pydantic: float = web.JsonBody(allow_inf_nan=True),
    short: str = web.JsonBody(min_length=3),
    long: str = web.JsonBody(max_length=10),
    regex: str = web.JsonBody(pattern=r'^\d*$'),
    precise: Decimal = web.JsonBody(max_digits=5, decimal_places=2),
) -> web.Response:
    return web.Response()

@routes.get('/schema')
async def handler_schema(
    body: Schema = web.JsonBodySchema(),
) -> web.Response:
    return web.Response()

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

### Validation Example
```python
from rapidy import web
from pydantic import BaseModel, Field

routes = web.RouteTableDef()

class BodyRequestSchema(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=40)

@routes.post('/api/{user_id}')
async def handler(
        user_id: str = web.Path(),
        host: str = web.Header(alias='Host'),
        body: BodyRequestSchema = web.JsonBodySchema(),
) -> web.Response:
    return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

#### Success request validation
```
curl -X POST \
-H "Content-Type: application/json" -d '{"username": "User", "password": "myAwesomePass"}' -v http://127.0.0.1:8080/api/1

< HTTP/1.1 200 OK ... {"data": "success"}
```

#### Failed request validation

```
curl -X POST \
-H "Content-Type: application/json" -d '{"username": "U", "password": "m"}' -v http://127.0.0.1:8080/api/1

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

### Types of request parameters
`rAPIdy` supports 3 basic types for defining incoming parameters:
* Param
* Schema
* Raw data

#### Single parameter
`Single` parameter, used when you need to spot-retrieve incoming data.

```python
from rapidy import web

async def handler(
        path_param: str = web.Path(),
        # headers
        host: str = web.Header(alias='Host'),
        user_agent: str = web.Header(alias='User-Agent'),
        # cookie
        user_cookie1: str = web.Cookie(alias='UserCookie1'),
        user_cookie2: str = web.Cookie(alias='UserCookie2'),
        # query params
        user_param1: str = web.Query(alias='UserQueryParam1'),
        user_param2: str = web.Cookie(alias='UserQueryParam2'),
        # body
        username: str = web.JsonBody(min_length=3, max_length=20),
        password: str = web.JsonBody(min_length=8, max_length=40),
) -> web.Response:
    # write your code here
    # ...
    return web.Response()

app = web.Application()
app.add_routes([web.post('/api/{path_param}', handler)])
```
> [!NOTE]
> All single parameters
> * Path
> * Header
> * Cookie
> * Query
> * BodyJson
> * FormDataBody
> * MultipartBody

#### Schema
`Schema-parameter` is useful when you want to extract a large amount of data.

```python
from rapidy import web
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

async def handler(
        path: PathRequestSchema = web.PathSchema(),
        headers: HeaderRequestSchema = web.HeaderSchema(),
        cookies: CookieRequestSchema = web.Cookie(),
        query: QueryRequestSchema = web.QuerySchema(),
        body: BodyRequestSchema = web.JsonBodySchema(),
) -> web.Response:
    # write your code here
    # ...
    return web.Response()

app = web.Application()
app.add_routes([web.post('/api/{path_param}', handler)])
```
> [!NOTE]
> All schema parameters
> * PathSchema
> * HeaderSchema
> * CookieSchema
> * QuerySchema
> * BodyJsonSchema
> * FormDataBodySchema
> * MultipartBodySchema

#### Raw
Use `Raw-parameter` when you don't need validation.

```python
from typing import Any
from rapidy import web

async def handler(
        path: dict[str, str] = web.PathRaw,
        headers: dict[str, str] = web.HeaderRaw,
        cookies: dict[str, str] =  web.CookieRaw,
        query: dict[str, str] = web.QueryRaw,
        body: dict[str, Any] = web.JsonBodyRaw,
) -> web.Response:
    # write your code here
    # ...
    return web.Response()

app = web.Application()
app.add_routes([web.post('/api/{path_param}', handler)])
```
> [!NOTE]
> All raw parameters
> * PathRaw - `dict[str, str]`
> * HeaderRaw - `dict[str, str]`
> * CookieRaw - `dict[str, str]`
> * QueryRaw - `dict[str, str]`
> * BodyJsonRaw - `dict[str, Any]`
> * FormDataBodyRaw - `dict[str, str]` or `dict[str, list[str]]`
> * MultipartBodyRaw - `dict[str, Any]` or `dict[str, list[Any]]`
> * TextBody - `str`
> * BytesBody - `bytes`
> * StreamBody - `aiohttp.streams.StreamReader`


#### Combining Different Approaches
```python
async def handler(
        path_param: str = web.Path(),
        headers: dict[str, str] = web.HeaderRaw(),
        body: BodyRequestSchema = web.JsonBodySchema(),
) -> web.Response:
```

### Ways to define metadata for a query parameter
There are a total of two ways to define query parameters.

1. **Using the Annotated Auxiliary Type**: Specify metadata directly within the Annotated type
2. **Using the Default Attribute Value**: Define the query parameter's default value along with its metadata


```python
from typing import Annotated  # use typing_extensions if py version == 3.8
from rapidy import web

async def handler(
        param_1: Annotated[str, web.JsonBody()],  # Annotated definition
        param_2: str = web.JsonBody(),  # Default definition
) -> web.Response:
```

### Special attributes

Some `rAPIdy-parameters` include additional attributes that are not found in `Pydantic`, offering extended functionality beyond standard data validation

#### Body
 Currently, only parameters of the body type include special attributes in `rAPIdy`

> [!WARNING]
> Additional attributes can only be specified for `Schema-parameters` and `Raw-parameters`.

In `rAPIdy`, the `body_max_size` attribute associated with each body parameter restricts the maximum allowable size of the request `body` for a specific handler

`body_max_size` (_int_) - indicating the maximum number of bytes the handler expects.

```python
async def handler(
        body: str = web.JsonBodySchema(body_max_size=10),
) -> web.Response:
```
```python
async def handler(
        body: str = web.JsonBodyRaw(body_max_size=10),
) -> web.Response:
```

##### Json
`json_decoder` (_typing.Callable[[], Any]_) - attribute that accepts the function to be called when decoding the body of the incoming request.

##### FormData
`attrs_case_sensitive` (_bool_) -  attribute that tells the data extractor whether the incoming key register should be considered.

`duplicated_attrs_parse_as_array` (_bool_) - attribute that tells the data extractor what to do with duplicated keys in a query.

If duplicated_attrs_parse_as_array=True, a list will be created for each key and all values will be placed in it.

> [!NOTE]
> `duplicated_attrs_parse_as_array` flat changes the type of data that the data extractor returns.
>
> If duplicated_attrs_parse_as_array=`True`, then the data
> will always be of type _dict[str, list[str]]_ (_by default, `formdata` has the extractable type dict[str, str]_)

##### Multipart

`attrs_case_sensitive` (_bool_) -  attribute that tells the data extractor whether the incoming key register should be considered.

`duplicated_attrs_parse_as_array` (_bool_) - attribute that tells the data extractor what to do with duplicated keys in a query.

> [!NOTE]
> `duplicated_attrs_parse_as_array` flat changes the type of data that the data extractor returns.
>
> If duplicated_attrs_parse_as_array=`True`, then the data
> will always be of type _dict[str, list[Any]]_ (_by default, `multipart` has the extractable type dict[str, Any]_)

---

### Catch client errors
The `HTTPValidationFailure` exception will be raised if the data in the query is incorrect.<br>
This error can be caught with a try/except block. The error values can be accessed using the `validation_errors` attribute.

This may be necessary, for example, if you need to log a customer error before giving them a response.

```python
import logging
from rapidy import web
from rapidy.typedefs import Handler
from rapidy.web_exceptions import HTTPValidationFailure

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

@routes.get('/')
async def handler(
        auth_token: str = web.Header(alias='Authorization'),
) -> web.Response:
    return web.json_response({'data': 'success'})

@web.middleware
async def error_catch_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    try:
        return await handler(request)

    except HTTPValidationFailure as validation_failure_error:
        client_errors = validation_failure_error.validation_errors
        logger.error('Client error catch, errors: %s', client_errors)
        raise validation_failure_error

    except Exception as unhandled_error:
        logger.error('Unhandled error: %s', unhandled_error)
        return web.json_response(status=500)

app = web.Application(middlewares=[error_catch_middleware])
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

## Default values for parameters
Some <span style="color:#7e56c2">rAPIdy</span> parameters may contain default values.

```python
async def handler(
        header_param_1: str = web.Header('default'),
        header_param_2: Annotated[str, web.Header()] = 'default',

        cookie_param_1: str = web.Cookie('default'),
        cookie_param_2: Annotated[str, web.Cookie()] = 'default',

        query_param_1: str = web.Query('default'),
        query_param_2: Annotated[str, web.Query()] = 'default',

        json_param_1: str = web.JsonBody('default'),
        json_param_2: Annotated[str, web.JsonBody()] = 'default',
) -> web.Response:
```
> [!NOTE]
> Default values support some single parameters and schemes
>
> Raw and Path parameters cannot have default values.
>
> Some body types do not contain `Raw` in their name, but they are also parameters that receive raw data, such as `StreamBody` or `TextBody`.
---


# Client
> [!TIP]
> Coming soon: 2024.09
---


# OpenAPI
> [!TIP]
> Already in development
>
> Coming soon: 2024.09
---


# Mypy support
`rAPIdy` has its own plugin for <a href="https://mypy.readthedocs.io/en/stable/getting_started.html" target="blank">mypy</a>.

```toml
# example for pyproject.toml
# ...
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"
]
# ...
```
---


# Migration from aiohttp to rAPIdy
`rAPIdy` neatly extends `aiohttp` - meaning that anything already written in `aiohttp` will work as before without any modifications

`rAPIdy` has exactly the same overridden module names as `aiohttp`.

> [!WARNING]
> `rAPIdy` does not override all `aiohttp` modules, only those that are necessary for it to work, or those that will be extended in the near future.

If the `aiohttp` module you are trying to override is not found in `rAPIdy`, don't change it, everything will work as is.

> [!WARNING]
> `rAPIdy` supports defining handlers in the same way as <a href="https://docs.aiohttp.org/en/stable/web_quickstart.html" target="blank">aiohttp-quickstart</a> except that request is no longer a required parameter for functional handlers.
>
> If you need to get the current `request` in the handler,
> create an attribute with an arbitrary name and be sure to specify the `web.Request` type, and rAPIdy will substitute the current `web.Request` instance in that place.
---


# For Developers
> [!TIP]
> Coming soon: 2024.06
