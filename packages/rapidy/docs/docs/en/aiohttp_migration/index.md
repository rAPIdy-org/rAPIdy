---
hide:
  - navigation
---

# Migration to Rapidy from aiohttp

## Description
`rapidy` carefully extends `aiohttp`, which means that all code written for `aiohttp` will work without modifications.

!!! info ""
    `rapidy` uses the same module names as `aiohttp`.

!!! note ""
    If the required object is not available in `rapidy`, it can be imported directly from `aiohttp`.

---

## `aiohttp` issues and their solutions in `Rapidy`
The `aiohttp` framework has a number of features and limitations that `Rapidy` addresses in a more convenient and elegant way.

### Simplified handling of the `request` parameter
In `aiohttp`, route handlers require an explicit `request` parameter, even if it is not used.

**Example (`aiohttp`):**
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/request/aiohttp.py !}
```

In `Rapidy`, the `request` parameter is not required, making the code more concise:

**Example (`Rapidy`):**
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/request/rapidy.py !}
```

!!! tip "Learn more about `Request` handling **[here](../docs/server/request)**."

---
### Simplified background task handling
In `aiohttp`, background task handlers require an explicit `app` parameter:
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/bg_tasks/aiohttp.py !}
```

In `Rapidy`, the `app` parameter is not required:
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/bg_tasks/rapidy.py !}
```

!!! tip "The `app` attribute can still be passed if needed, learn more **[here](../docs/lifespan)**."
!!! tip "Learn more about background task handling **[here](../docs/lifespan)**."

---

### Improved class-based handler routing
In `aiohttp`, class-based handler routing is tied to HTTP method names, limiting flexibility.

In `Rapidy`, handlers can be conveniently grouped:
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/class_handlers/rapidy.py !}
```

!!! tip "Learn more about HTTP handler functionality **[here](../docs/server/handlers)**."

---

### Simple data validation and serialization
In `Rapidy`, request data can be easily validated and serialized using `pydantic`:
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/validation/rapidy.py !}
```

---

### Simpler Application Modularization
In `aiohttp`, adding sub-applications requires explicit route additions and `Application` object initialization:
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/sub_apps/aiohttp.py !}
```

In `Rapidy`, this process is simpler:
```python
{!> ./docs/aiohttp_migration/01_aiohttp_problems/sub_apps/rapidy.py !}
```

---

### Key Advantages of `Rapidy`
- **More concise code**: Reduces boilerplate without sacrificing readability.
- **Convenient routing**: Allows grouping handlers within classes.
- **Flexible data validation and serialization**: Built-in `pydantic` support.
- **Simplified request and response handling**: Access `Request` and `Response` via type annotations.
- **Advanced application lifecycle management**: Easy-to-use `on_startup`, `on_shutdown`, and `on_cleanup` hooks.
- **Better integration with Python’s async capabilities**: Fewer unnecessary parameters and less manual data handling.

!!! tip "Learn more about `Rapidy` features **[here](../docs)**."

## How to migrate from `aiohttp` to `Rapidy`

Migrating from `aiohttp` to `Rapidy` simplifies code, removes boilerplate, improves validation, and makes dependency management easier.

### Full migration
Suppose you have an `aiohttp` application with a request handler, request parameters, validation, and lifecycle hooks:

**Code in `aiohttp`:**
```python
{!> ./docs/aiohttp_migration/02_migration/full/aiohttp.py !}
```

**Code in `Rapidy`:**
```python
{!> ./docs/aiohttp_migration/02_migration/full/rapidy.py !}
```

Key improvements:

- **Less boilerplate** — No explicit `request: web.Request`, `Rapidy` automatically parses and validates JSON using `pydantic`.
- **Simplified lifecycle management** — `on_startup` is passed as a list instead of using `app.on_startup.append()`.
- **Routing without `app.add_routes()`** — Handlers are provided via `http_route_handlers`.

---

### Partial migration
Sometimes a full migration is not immediately possible, such as when new functionality needs to be added while retaining some `aiohttp` code.
In this case, you can transition gradually.

This approach allows you to migrate code to `Rapidy` by replacing parts of `aiohttp` with the new syntax without rewriting the entire project.

#### Adding small features
Suppose you need to retrieve the `Host` header and include it in the response without changing the rest of the logic.

**Before (`aiohttp`)**:
```python
{!> ./docs/aiohttp_migration/02_migration/partial/minor/aiohttp.py !}
```

**After (`Rapidy`)**:
```python hl_lines="1 13 19 20"
{!> ./docs/aiohttp_migration/02_migration/partial/minor/rapidy.py !}
```

Changes:

1. Updated imports.
2. Added `host: str = web.Header(alias='Host')` in the `create_user` HTTP handler.
3. Replaced `json_response` with `Response`, as its functionality is now built into `Response`.

!!! tip "`Response` in `Rapidy` offers more features, learn more **[here](../docs/server/response)**."

!!! info "Rapidy can do (almost) everything"
    The example above shows how to extend code using `web.RouteTableDef()`,
    but `Rapidy` also supports all other `aiohttp` handler declaration styles.
    Learn more about `aiohttp`-style handlers **[here](../docs/server/handlers)**.

#### Adding new functionality via sub-applications
You can easily extend an existing `aiohttp` application by adding new functionality through sub-applications.

**Before (`aiohttp`)**:
```python
{!> ./docs/aiohttp_migration/02_migration/partial/subapp/aiohttp.py !}
```

**After (`Rapidy`)**:
```python hl_lines="1 2 14 20 21 22 24 27"
{!> ./docs/aiohttp_migration/02_migration/partial/subapp/rapidy.py !}
```

This approach enables seamless integration of `Rapidy` into existing code without requiring significant modifications.

!!! warning "However, you will need to update `aiohttp` imports to `rapidy` and replace `json_response` with `Response` throughout your code."
