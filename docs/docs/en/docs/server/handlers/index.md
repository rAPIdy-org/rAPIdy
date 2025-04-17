# Routing and Creating HTTP Handlers
Web handlers are designed to process incoming HTTP requests.

In `Rapidy`, routing and handler creation are closely related: routing determines which handler will be invoked in response to a request.

## Defining Routes
A route is a `URL` string that triggers a handler.

There are two types of routes: static and dynamic.

!!! info "Difference Between Static and Dynamic Routing"
    | Route Type  | Example URL        | Description |
    | ----------- | ------------------ | ----------- |
    | Static      | /about             | The URL is fixed. |
    | Dynamic     | /users/{user_id}   | The URL changes depending on parameters. |

!!! info ""
    `Rapidy` supports multiple ways of defining routes similar to `aiohttp`. More details on this are provided below in the section `Creating and Registering HTTP Handlers`.

    You can learn more about `aiohttp` handlers **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

---

### Static Routes
Static HTTP routing is a type of routing where the path (URL) is predefined and does not change dynamically.
This means that every request to a specific route always leads to the same handler.

**Simple Static Route**
```python hl_lines="3"
from rapidy.http import get

@get('/hello_rapidy')
async def handler() -> str:
    return 'Hello Rapidy!'
```

!!! info "This route is always available via `GET /hello` and returns the same response."
    ```shell
    curl http://localhost:8000/hello_rapidy
    ```

Similarly, you can define other methods such as `get`, `post`, `put`, `delete`, and so on.

### Dynamic Routes
Dynamic routing allows you to define routes that accept variable parameters.
This is useful when working with different entities (e.g., `user_id`, `post_id`, etc.) by passing them in the `URL`.

!!! info "The examples below use `PathParam`, which is required for extracting path parameters. You can read more about it [here](../request/parameters/path)."

#### Simple Dynamic Route

Suppose we have an API to retrieve user information based on `user_id`:

```python hl_lines="3"
from rapidy.http import get, PathParam

@get('/users/{user_id}')
async def handler(user_id: int = PathParam()) -> dict[str, int]:
    return {'user_id': user_id}
```

How does this route work?

1. `user_id` is a dynamic parameter passed in the URL.
2. `Rapidy` automatically converts it to `int` (if a string is passed, the API will return a `422` error).

Example request:
```shell
curl http://localhost:8000/users/123
```

Response:
```text
{"user_id": 123}
```

#### Dynamic Routes with Multiple Parameters

You can add multiple dynamic parameters:
```python hl_lines="3"
from rapidy.http import get, PathParam

@get('/posts/{post_id}/comments/{comment_id}')
async def handler(
    post_id: int = PathParam(),
    comment_id: int = PathParam(),
) -> dict[str, int]:
    return {'post_id': post_id, 'comment_id': comment_id}
```

Now, the request `GET /posts/10/comments/5` will return:
```text
{"post_id": 10, "comment_id": 5}
```

### Grouping Routes
If you have many routes, you can use one of the available approaches to group HTTP requests.

!!! note "It is recommended to stick to a single approach within a project."

#### HTTPRouter
`Rapidy` provides an `HTTPRouter` object for grouping requests.

`HTTPRouter` allows registering groups of handlers and plays a key role in routing by directing requests to the appropriate handlers based on the HTTP method,
path, parameters, and other conditions.

!!! info "`HTTPRouter` is registered just like any other HTTP handler."

```python
from rapidy import Rapidy
from rapidy.http import HTTPRouter, controller, get

@get('/healthcheck')  # /healthcheck
async def healthcheck() -> str:
    return 'ok'

@get('/hello')  # /api/hello
async def hello_handler() -> dict[str, str]:
    return {'hello': 'rapidy'}

api_router = HTTPRouter('/api', [hello_handler])

rapidy = Rapidy(http_route_handlers=[healthcheck, api_router])
```

!!! tip "`HTTPRouter` can do more!"
    `HTTPRouter` also has several attributes that extend its capabilities, such as `middleware` handling, background task management, and more.

    You can also create nested `HTTPRouter` instances.

    You can read more about `HTTPRouter` [here](http_router).

---

## Creating and Registering HTTP Handlers

### Functional Handlers

The simplest way to create a handler:
```Python
{!> ./docs/docs/server/handlers/01_func_handler.py !}
```

#### Examples of Handler Registration

??? example "Registering a Handler Without a Decorator"
    ```Python
    {!> ./docs/docs/server/handlers/02_func_handler_no_deco.py !}
    ```

??? example "Adding a Handler via the Application `router` _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/03_func_handler_add_method_aio_style.py !}
    ```

    !!! info "Supported methods correspond to HTTP methods with the `add_` prefix."
    - `add_get`
    - `add_post`
    - `add_put`
    - `add_patch`
    - `add_delete`

    !!! note "Exception — `view`."
        - `add_view`

??? example "Adding a Handler with a Decorator via `RouteTableDef` _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/04_func_handler_routetable_deco.py !}
    ```

??? example "Adding a Handler Without a Decorator via `rapidy.web` _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/05_func_handler_app_add_routes.py !}
    ```

---

### Class-Based Handlers

Class-based handlers allow grouping multiple methods within a single class:
```Python
{!> ./docs/docs/server/handlers/06_controller_handler.py !}
```

#### Examples of Class-Based Handler Registration

??? example "Registering a Handler Without a Decorator"
    ```Python
    {!> ./docs/docs/server/handlers/07_controller_handler_no_deco.py !}
    ```

##### Using `View` _(aiohttp style)_
??? example "Adding a Handler via the Application `router` _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/08_view_router.py !}
    ```

??? example "Adding a Handler via `router` with Different Paths _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/09_view_router_different_path.py !}
    ```

??? example "Adding a Handler with a Decorator via `RouteTableDef` _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/10_view_routetabledef.py !}
    ```

??? example "Adding a Handler with a Decorator via `RouteTableDef` with Different Paths _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/11_view_routetabledef_different_path.py !}
    ```

??? example "Adding a Handler Without a Decorator via `rapidy.web` _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/12_view_add_routes.py !}
    ```

??? example "Adding a Handler Without a Decorator via `rapidy.web` with Different Paths _(aiohttp style)_"
    ```Python
    {!> ./docs/docs/server/handlers/13_view_add_routes_different_path.py !}
    ```

---

## Handler Attributes
Attributes allow managing handler behavior and responses.

Attributes are automatically applied to handler responses if the handler returns anything other than `Response`
_(does not apply to `path` and `allow_head` attributes for the `get` method)_.

!!! example "Attributes are applied to responses."
    The `response_content_type` attribute will be applied to each handler response
    because the handler returns a `python` object.
    ```python
    from rapidy.http import get, ContentType

    @get('/', response_content_type=ContentType.text_plain)
    async def handler() -> str:
        return 'Hello Rapidy!'
    ```

!!! example "Attributes are not applied to responses."
    The `response_content_type` attribute will not be applied to the handler response
    because the handler returns a low-level `Response` object.
    ```python
    from rapidy.http import get, ContentType, Response

    @get('/', response_content_type=ContentType.text_plain)
    async def handler() -> Response:
        return Response('Hello Rapidy!')
    ```

!!! info "All handler creation methods support the same attributes for managing web requests."

### Core Attributes (Always Applied)
#### path
**`path`**: `str` — the handler's route on the server.
```python hl_lines="2"
{!> ./docs/docs/server/handlers/attrs/path.py !}
```

---

#### allow_head
**`allow_head`**: `bool = True` — if set to `True` (default), a route is added for the `head` method with the same handler as `get`.

```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/allow_head.py !}
```

!!! note "This attribute can only be applied to the `get` method."

---

### Response Validation

#### response_validate
**`response_validate`**: `bool = True` — whether to validate the handler response.
```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/response_validate.py !}
```

---

#### response_type
**`response_type`**: `Type[Any] | None = ...` — defines the response type (overrides return annotation).
```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/response_type.py !}
```

!!! note "This flag adds flexibility for serialization and validation but is rarely used."

---

### Managing Headers and Encoding

#### response_content_type
**`response_content_type`**: `str = 'application/json'` — an attribute that allows managing the `Content-Type` header.

The `Content-Type` header informs the client (browser, API client, another server) about the type of data contained in the HTTP response body.

```python hl_lines="5"
{!> ./docs/docs/server/handlers/attrs/response_content_type/index.py !}
```

!!! note "If `content_type` is specified, the provided data will be converted accordingly."

!!! note "If `content_type` is not specified, it will be determined automatically based on the type of data returned by the server."

??? example "content_type="application/json"
    `content_type="application/json"` — data is converted to `JSON` using [jsonify(dumps=True)](../../encoders)
    and encoded according to [response_charset](#response_charset).

    ```python hl_lines="5"
    {!> ./docs/docs/server/handlers/attrs/response_content_type/json_dict.py !}
    ```

    !!! note ""
        If the provided object is a string `Response(body="string")`, then the string, according to the **JSON** standard, will be escaped twice:
        ```python hl_lines="5"
        {!> ./docs/docs/server/handlers/attrs/response_content_type/json_str.py !}
        ```

??? example "content_type="text/*"
    `content_type="text/*"` *(any text type: `text/plain`, `text/html`, etc.)* - if the data is of type `str`, it is sent as is.
    Otherwise, it is converted to a string via [jsonify(dumps=False)](../../encoders).

    ```python hl_lines="5"
    {!> ./docs/docs/server/handlers/attrs/response_content_type/text.py !}
    ```

    !!! info ""
        If the object is still not a string after `jsonify(dumps=False)`, it is further converted using [response_json_encoder](#response_json_encoder).

??? example "content_type - any other MIME type."
    If the data is of type `bytes`, it is sent as is.
    Otherwise, it is converted to a string using [jsonify(dumps=True)](../../encoders) and encoded according to [response_json_encoder](#response_json_encoder).

!!! info "If `content_type` is not specified, it is set automatically:"

    - `body: dict | BaseModel | dataclass` → `content_type="application/json"`
        ```python
        async def handler() -> dict[str, str]:
            return {"hello": "rapidy"}

        async def handler() -> SomeModel:
            return SomeModel(hello="rapidy")  # `SomeModel` inherits from `pydantic.BaseModel`
        ```

    - `body: str | Enum | int | float | Decimal | bool` → `content_type="text/plain"`
        ```python
        async def handler() -> str:
            return 'string'

        async def handler() -> str:
            return SomeEnum.string

        async def handler() -> int:
            return 1

        async def handler() -> float:
            return 1.0

        async def handler() -> Decimal:
            return Decimal("1.0")

        async def handler() -> bool:
            return True
        ```

    - `body: Any` → `content_type="application/octet-stream"`
        ```python
        async def handler() -> bytes:
            return b'bytes'

        async def handler() -> AnotherType:
            return AnotherType()
        ```

---

#### response_charset
**`response_charset`**: `str = 'utf-8'` — the encoding used for response data.

```python hl_lines="5"
{!> ./docs/docs/server/handlers/attrs/response_charset.py !}
```

---

#### response_json_encoder
**`response_json_encoder`**: `Callable = json.dumps` — a function that takes an object and returns its JSON representation.

Automatically applied to any Python object after validation through `pydantic`.
```python hl_lines="8"
{!> ./docs/docs/server/handlers/attrs/response_json_encoder.py !}
```

---

### Data Compression

#### response_zlib_executor
**`response_zlib_executor`**: `concurrent.futures.Executor | None = None` — `zlib` compression function.
```python hl_lines="8"
{!> ./docs/docs/server/handlers/attrs/response_zlib_executor.py !}
```
!!! note "More about `zlib_executor`"
    `zlib_executor` is an `aiohttp` mechanism. More details **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

---

#### response_zlib_executor_size
**`response_zlib_executor_size`**: `int | None = None` — body size in bytes to enable compression.
```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/response_zlib_executor_size.py !}
```

---

### Managing Pydantic Fields

#### response_include_fields
**`response_include_fields`**: `set[str] | dict[str, Any] | None = None` — `include` parameter from `Pydantic`, specifying which fields to include.
```python hl_lines="9"
{!> ./docs/docs/server/handlers/attrs/response_include_fields.py !}
```

---

#### response_exclude_fields
**`response_exclude_fields`**: `set[str] | dict[str, Any] | None` — list of fields to exclude.
```python hl_lines="9"
{!> ./docs/docs/server/handlers/attrs/response_exclude_fields.py !}
```

---

#### response_by_alias
**`response_by_alias`**: `bool = True` — whether to use `Pydantic` aliases.
```python hl_lines="8 17"
{!> ./docs/docs/server/handlers/attrs/response_by_alias.py !}
```

---

#### response_exclude_unset
**`response_exclude_unset`**: `bool = False` — whether to exclude default values.
```python hl_lines="9 18"
{!> ./docs/docs/server/handlers/attrs/response_exclude_unset.py !}
```

---

#### response_exclude_defaults
**`response_exclude_defaults`**: `bool = False` — whether to exclude explicitly set values if they match the defaults.
```python hl_lines="8 17"
{!> ./docs/docs/server/handlers/attrs/response_exclude_defaults.py !}
```

---

#### response_exclude_none
**`response_exclude_none`**: `bool = False` — whether to exclude `None` values.
```python hl_lines="9 18"
{!> ./docs/docs/server/handlers/attrs/response_exclude_none.py !}
```

---

#### response_custom_encoder
**`response_custom_encoder`**: `Dict[Any, Callable[Any], Any]] | None = None` — `custom_encoder` parameter from `Pydantic`, allowing a custom encoder to be specified.
