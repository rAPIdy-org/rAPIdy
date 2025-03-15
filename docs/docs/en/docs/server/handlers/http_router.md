# HTTPRouter

## Description
`HTTPRouter` allows registering groups of handlers and plays a key role in routing, directing requests to the appropriate handlers based on HTTP methods, paths,
parameters, and other conditions.

!!! info "HTTPRouter is registered in the same way as any HTTP handler."

```python hl_lines="12 14"
{!> ./docs/docs/server/handlers/http_router/index.py !}
```

!!! warning "`HTTPRouter` does not support handler registration in the `aiohttp` style."
    None of the `aiohttp` style handler registration methods will work.

    If you need to register an HTTP handler in `HTTPRouter`, use the methods from the `rapidy.http` module (`get`, `post`, ...).

### Nested Routers (`HTTPRouter`)
`HTTPRouter` can be nested within each other, allowing for the creation of modular applications.

This is useful, for example, for API versioning.

```python hl_lines="12 13 15 17"
{!> ./docs/docs/server/handlers/http_router/sub_routes.py !}
```

!!! example "Each `HTTPRouter` can have its own middleware."

    This allows, for example, applying different authentication mechanisms to different route groups.

    ```python hl_lines="21 22 24 26"
    {!> ./docs/docs/server/handlers/http_router/sub_routes_auth.py !}
    ```

## `HTTPRouter` Attributes

### path
**`path`**: `str` — the handler's route on the server.

```python hl_lines="4"
{!> ./docs/docs/server/handlers/http_router/attrs/path.py !}
```

---

### route_handlers
**`route_handlers`**: `Iterable[BaseHTTPRouter] = ()` — a list of route handlers.
It can include both individual handlers and nested `HTTPRouter` instances.

```python hl_lines="9"
{!> ./docs/docs/server/handlers/http_router/attrs/route_handlers.py !}
```

---

### middlewares
**`middlewares`**: `Optional[Iterable[Middleware]] = None` — a list of middleware
applied to all handlers, including child routers.

```python hl_lines="11"
{!> ./docs/docs/server/handlers/http_router/attrs/middlewares.py !}
```

!!! info "Read more about `Middlewares` [here](../../middlewares)."

---

### client_max_size
**`client_max_size`**: `int = 1024**2` — The maximum request size in bytes.

```python hl_lines="5"
{!> ./docs/docs/server/handlers/http_router/attrs/client_max_size.py !}
```

---

## Lifecycle Management
`HTTPRouter` supports lifecycle management just like the main application.

!!! info "Read more about `Lifespan` [here](../../lifespan)."

#### on_startup
**`on_startup`**: `Optional[List[LifespanHook]]` — a list of tasks executed when the application starts.

```python hl_lines="8"
{!> ./docs/docs/server/handlers/http_router/attrs/on_startup.py !}
```

---

#### on_shutdown
**`on_shutdown`**: `Optional[List[LifespanHook]]` — tasks executed when the server shuts down.

```python hl_lines="8"
{!> ./docs/docs/server/handlers/http_router/attrs/on_shutdown.py !}
```

---

#### on_cleanup
**`on_cleanup`**: `Optional[List[LifespanHook]]` — tasks executed after `on_shutdown`.

```python hl_lines="8"
{!> ./docs/docs/server/handlers/http_router/attrs/on_cleanup.py !}
```

---

#### lifespan
**`lifespan`**: `Optional[List[LifespanCTX]] = None` — a list of context managers
that support application lifecycle management.

```python hl_lines="16"
{!> ./docs/docs/server/handlers/http_router/attrs/lifespan.py !}
```
