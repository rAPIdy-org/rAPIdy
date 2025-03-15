# Application
## Description
`Application` is the core of the web server responsible for handling all incoming requests.

It allows you to register and manage:

- Web handlers *(endpoint)*
- Middleware
- Sub-applications
- Background tasks

!!! note "`rapidy.Rapidy` is an alias for `rapidy.web.Application`"

## Application Entities
### Endpoint
An **endpoint** is a final point of a web service that a client application interacts with to perform specific operations or retrieve data, such as `/api/user/get-data`.
```python
{!> ./docs/docs/server/application/01_simple_endpoint.py !}
```
!!! info "For more details on creating an `endpoint`, see the [Handlers](../handlers) section."

---

### Middleware
`Middleware` allows you to perform actions on a request before and after it is processed by a web handler.
```python
{!> ./docs/docs/server/application/02_simple_auth_middleware.py !}
```
!!! info "For more details on creating `middleware`, see the [Middlewares](../middlewares/index) section."

??? example "Applying `middleware` for different API versions."
    ```python
    {!> ./docs/docs/server/application/03_different_api_flow_middleware.py !}
    ```

---

### Routing
This section demonstrates how to organize groups of `web handlers`.

??? example "Example of bad practice."
    ```python
    {!> ./docs/docs/server/application/04_sub_path_bad_practice.py !}
    ```
    !!! tip "It is recommended to use `rapidy.http.HTTPRouter` or child `rapidy.web.Application` instead."

#### HTTPRouter
Using `HTTPRouter` makes the code more concise and convenient.
```python
{!> ./docs/docs/server/application/05_http_router/example.py !}
```
```shell
{!> ./docs/docs/server/application/05_http_router/curl.sh !}
```

!!! info "For more details on `HTTPRouter`, see the [HTTPRouter](../handlers/http_router) section."

#### Sub-application *(aiohttp-style)*
Creating child `Application`:
```python
{!> ./docs/docs/server/application/06_sub_app/example.py !}
```
```bash
{!> ./docs/docs/server/application/06_sub_app/curl.sh !}
```

!!! note "Using child applications in the `aiohttp` style for new code is not recommended."

---

### Lifespan
**Lifespan** is a mechanism for managing the lifecycle of background tasks in `Rapidy`.

It controls tasks that should be executed: before or after the server starts, as well as tasks that should run continuously.
```python
{!> ./docs/docs/server/application/07_lifespan.py !}
```
!!! info "For more details on `lifespan`, see the [Lifespan](../../lifespan) section."

---

## Application Attributes
### Additional Attributes in `Rapidy`
##### server_info_in_response
Defines whether to include server information in the `Server` header.
```python
server_info_in_response: bool = False
```

##### lifespan
A list of background tasks that start and stop along with the server.
```python
lifespan: Optional[List[LifespanCTX]] = None
```

##### on_startup
A list of tasks executed immediately after the application starts.
```python
on_startup: Optional[List[LifespanHook]] = None
```

##### on_shutdown
Tasks executed when the server stops.
```python
on_shutdown: Optional[List[LifespanHook]] = None
```

##### on_cleanup
Tasks executed after `on_shutdown`.
```python
on_cleanup: Optional[List[LifespanHook]] = None
```

##### http_route_handlers
HTTP routers that can be either individual handlers or groups of `HTTPRouter`.
```python
http_route_handlers: Iterable[HTTPRouterType] = ()
```

### `aiohttp` Attributes
##### middlewares
A list of `middleware` applied to all handlers, including child applications.
```python
middlewares: Optional[Iterable[Middleware]] = None
```

##### client_max_size
Maximum request size in bytes.
```python
client_max_size: int = 1024**2
```

##### logger
Logger for receiving logs from `Application`.
```python
logger: logging.Logger = logging.getLogger("aiohttp.web")
```

## Running the Application
### Simple Run
Copy the following code into `main.py`.
```Python hl_lines="12"
{!> ./docs/docs/server/application/08_runserver/run_app.py !}
```
Start the server:
```bash
{!> ./docs/docs/server/application/08_runserver/run_app.sh !}
```
!!! note "You can specify parameters like `host` or `port`."
    ```python
    {!> ./docs/docs/server/application/08_runserver/run_app_change_host_and_port.py !}
    ```

### WSGI Run (Gunicorn)
Install `gunicorn`:
```bash
pip install gunicorn
```
Copy the following code into `main.py`:
```Python
{!> ./docs/docs/server/application/08_runserver/gunicorn.py !}
```
Start the server:
```shell
{!> ./docs/docs/server/application/08_runserver/gunicorn.sh !}
```

The `gunicorn main:app` command refers to:

* `main`: the `main.py` file (Python module).
* `rapidy`: the object created inside `main.py` in the line `rapidy = Rapidy()`.
* `--reload`: restarts the server when the code changes. Use only for development.
