---
hide:
  - navigation
---

# Quickstart
## Creating Simple Handlers
<a href="https://github.com/daniil-grois/rAPIdy" target="_blank">rAPIdy</a>
is based on
<a href="https://github.com/aio-libs/aiohttp" target="_blank">aiohttp</a>
and supports all types of handler definitions.<br/>
Below, only the main types will be shown.
!!! tip "You can check all the available definitions **[here](../docs/server/handlers)**"

### Functional Handlers
```Python hl_lines="4"
{!> ./docs/quickstart/01_func_handler.py !}
```
??? example "Registration without decorator"
    ```Python hl_lines="9"
    {!> ./docs/quickstart/02_func_handler_no_deco.py !}
    ```

---

### Class-based Handlers
```Python hl_lines="4"
{!> ./docs/quickstart/03_controller_handler.py !}
```

??? example "Registration without decorator"
    ```Python hl_lines="15"
    {!> ./docs/quickstart/04_controller_handler_no_deco.py !}
    ```

## Middleware
Middleware are intermediate components that handle requests and responses at the web framework level.

They allow performing additional actions before and/or after the request is processed by the main handler.

```Python hl_lines="2 3 5 16"
{!> ./docs/quickstart/05_middleware.py !}
```

!!! info "Note"
    In the middleware handler,
    <b><span class="note-color">the first argument</span></b>
    should always be the <span class="note-color">Request</span>, and the second — <span class="note-color">call_next</span>.

## HTTPRoute
`HTTPRoute` allows you to register groups of handlers and plays a key role in routing,
helping to direct requests to the appropriate handlers based on the HTTP method, path, parameters, and other conditions.

!!! info "`HTTPRoute` is registered in exactly the same way as any HTTP handler."

```Python hl_lines="14 16"
{!> ./docs/quickstart/06_router.py !}
```

??? example "Registering handlers in the router without a decorator"
    ```Python hl_lines="15 16 20"
    {!> ./docs/quickstart/07_router_no_deco.py !}
    ```

??? example "Full example of registering a router and handlers"
    ```Python hl_lines="24 28 29 30"
    {!> ./docs/quickstart/08_router_full_example.py !}
    ```

## Simple Validation Example
```Python hl_lines="6 19 25 28"
{!> ./docs/quickstart/09_validation.py !}
```

## Running the Web Server
### Simple Start
Copy the code into the `main.py` file.
```Python hl_lines="12"
{!> ./docs/quickstart/10_runserver/run_app.py !}
```

Run the server in real-time mode:
```bash
{!> ./docs/quickstart/10_runserver/run_app.sh !}
```

!!! note "You can also specify various startup parameters, such as `host` or `port`."
    ```python
    {!> ./docs/quickstart/10_runserver/run_app_change_host_and_port.py !}
    ```

### WSGI Start (Gunicorn)
<span class="green-color">Gunicorn</span> is a Python WSGI HTTP server for UNIX.

??? note "What is WSGI"
    WSGI (Web Server Gateway Interface) is a simple and universal interface between the Web server and the Web application,
    first described in <a href="http://www.python.org/dev/peps/pep-0333/" target="_blank">PEP-333</a>.

!!! note "More about <a href="https://gunicorn.org/" target="_blank">gunicorn.org</a>"

Add Gunicorn to your project:

```bash
pip install gunicorn
```

Copy the code into the `main.py` file.
```Python hl_lines="6"
{!> ./docs/quickstart/10_runserver/gunicorn.py !}
```

Run the command in the terminal:
```bash
{!> ./docs/quickstart/10_runserver/gunicorn.sh !}
```

The `gunicorn main:rapidy` command accesses:

* `main`: the `main.py` file (Python module).
* `rapidy`: an object created inside the `main.py` file in line `rapidy = Rapidy()`.
* `--reload`: restarts the server after the code is modified. Use only for development.
