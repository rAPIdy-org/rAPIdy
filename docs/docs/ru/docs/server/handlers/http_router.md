# HTTPRouter

## Описание
`HTTPRouter` позволяет регистрировать группы обработчиков и играет ключевую роль в маршрутизации (routing), направляя запросы к нужным обработчикам в
зависимости от HTTP-метода, пути, параметров и других условий.

!!! info "`HTTPRouter` регистрируется так же, как и любой HTTP-обработчик."

```python hl_lines="12 14"
{!> ./docs/docs/server/handlers/http_router/index.py !}
```

!!! warning "`HTTPRouter` не поддерживает регистрацию обработчиков в стиле `aiohttp`."
    Ни один из способов регистрации обработчиков в стиле `aiohttp` работать не будет.

    Если вам нужно зарегистрировать HTTP-обработчик в `HTTPRouter`, пользуйтесь методами модуля `rapidy.http` (`get`, `post`, ...).

### Вложенные маршрутизаторы (`HTTPRouter`)
`HTTPRouter` можно вкладывать друг в друга, что позволяет создавать модульные приложения.

Это полезно, например, для версионирования API.

```python hl_lines="12 13 15 17"
{!> ./docs/docs/server/handlers/http_router/sub_routes.py !}
```

!!! example "Каждому `HTTPRouter` можно передать собственные middleware."

    Это позволяет, например, применять разные механизмы авторизации для разных групп маршрутов.

    ```python hl_lines="21 22 24 26"
    {!> ./docs/docs/server/handlers/http_router/sub_routes_auth.py !}
    ```

## Атрибуты `HTTPRouter`

### path
**`path`**: `str` — маршрут обработчика на сервере.

```python hl_lines="4"
{!> ./docs/docs/server/handlers/http_router/attrs/path.py !}
```

---

### route_handlers
**`route_handlers`**: `Iterable[BaseHTTPRouter] = ()` — список обработчиков маршрутов.
Может включать как отдельные обработчики, так и вложенные `HTTPRouter`.

```python hl_lines="9"
{!> ./docs/docs/server/handlers/http_router/attrs/route_handlers.py !}
```

---

### middlewares
**`middlewares`**: `Optional[Iterable[Middleware]] = None` — список middleware,
которые применяются ко всем обработчикам, включая дочерние маршрутизаторы.

```python hl_lines="11"
{!> ./docs/docs/server/handlers/http_router/attrs/middlewares.py !}
```

!!! info "Подробнее про `Middlewares` можно прочитать [здесь](../../middlewares)."

---

### client_max_size
**`client_max_size`**: `int = 1024**2` — Максимальный размер запроса в байтах.

```python hl_lines="5"
{!> ./docs/docs/server/handlers/http_router/attrs/client_max_size.py !}
```

---

## Управление жизненным циклом
`HTTPRouter` поддерживает управление жизненным циклом так же, как и основное приложение.

!!! info "Подробнее про `Lifespan` можно прочитать [здесь](../../lifespan)."

#### on_startup
**`on_startup`**: `Optional[List[LifespanHook]]` — список задач, запускаемых при старте приложения.

```python hl_lines="8"
{!> ./docs/docs/server/handlers/http_router/attrs/on_startup.py !}
```

---

#### on_shutdown
**`on_shutdown`**: `Optional[List[LifespanHook]]` — задачи, выполняемые при остановке сервера.

```python hl_lines="8"
{!> ./docs/docs/server/handlers/http_router/attrs/on_shutdown.py !}
```

---

#### on_cleanup
**`on_cleanup`**: `Optional[List[LifespanHook]]` — задачи, выполняемые после `on_shutdown`.

```python hl_lines="8"
{!> ./docs/docs/server/handlers/http_router/attrs/on_cleanup.py !}
```

---

#### lifespan
**`lifespan`**: `Optional[List[LifespanCTX]] = None` — список контекстных менеджеров,
поддерживающих управление жизненным циклом приложения.

```python hl_lines="16"
{!> ./docs/docs/server/handlers/http_router/attrs/lifespan.py !}
```
