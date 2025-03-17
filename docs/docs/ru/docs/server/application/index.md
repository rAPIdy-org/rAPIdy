# Веб-приложение
## Описание
`Application` — это сердце веб-сервера, отвечающее за обработку всех входящих запросов.

С его помощью можно регистрировать и управлять:

- веб-обработчиками *(endpoint)*
- промежуточными обработчиками *(middleware)*
- дочерними приложениями
- фоновыми задачами

!!! note "`rapidy.Rapidy` является псевдонимом для `rapidy.web.Application`"

## Сущности Application
### Endpoint
**Endpoint** — это конечная точка веб-сервиса, к которой клиентское приложение обращается для выполнения
определённых операций или получения данных, например, `/api/user/get-data`.
```python
{!> ./docs/docs/server/application/01_simple_endpoint.py !}
```
!!! info "Подробнее о создании `endpoint` смотрите в разделе [Handlers](../handlers)."

---

### Middleware
`Middleware` позволяют выполнять действия над запросом до и после его обработки веб-обработчиком.
```python
{!> ./docs/docs/server/application/02_simple_auth_middleware.py !}
```
!!! info "Подробнее о создании `middleware` смотрите в разделе [Middlewares](../middlewares/)."

??? example "Применение `middleware` для разных версий API."
    ```python
    {!> ./docs/docs/server/application/03_different_api_flow_middleware.py !}
    ```

---

### Routing
Здесь показано, как можно организовывать группы `web-обработчиков`.

??? example "Пример плохой практики."
    ```python
    {!> ./docs/docs/server/application/04_sub_path_bad_practice.py !}
    ```
    !!! tip "Рекомендуется использовать `rapidy.http.HTTPRouter` или дочерние `rapidy.web.Application`."

#### HTTPRouter
Использование `HTTPRouter` делает код более лаконичным и удобным.
```python
{!> ./docs/docs/server/application/05_http_router/example.py !}
```
```shell
{!> ./docs/docs/server/application/05_http_router/curl.sh !}
```

!!! info "Подробнее о `HTTPRouter` смотрите в разделе [HTTPRouter](../handlers/http_router)."

#### Подприложение *(aiohttp-style)*
Создание дочерних `Application`:
```python
{!> ./docs/docs/server/application/06_sub_app/example.py !}
```
```bash
{!> ./docs/docs/server/application/06_sub_app/curl.sh !}
```

!!! note "Использование дочерних приложений в стиле `aiohttp` при написании нового кода не рекомендуется."

---

### Lifespan
**Lifespan** — это механизм управления жизненным циклом фоновых задач в `Rapidy`.

Он управляет задачами, которые должны запускаться: до или после старта сервера, а также работать постоянно.
```python
{!> ./docs/docs/server/application/07_lifespan.py !}
```
!!! info "Подробнее о `lifespan` смотрите в разделе [Lifespan](../../lifespan)."

---

## Атрибуты Application
### Дополнительные атрибуты в `Rapidy`
##### server_info_in_response
Определяет, нужно ли включать информацию о сервере в заголовке `Server`.
```python
server_info_in_response: bool = False
```

##### lifespan
Список фоновых задач, которые запускаются и завершаются вместе с сервером.
```python
lifespan: Optional[List[LifespanCTX]] = None
```

##### on_startup
Список задач, запускаемых сразу после старта приложения.
```python
on_startup: Optional[List[LifespanHook]] = None
```

##### on_shutdown
Задачи, выполняемые при остановке сервера.
```python
on_shutdown: Optional[List[LifespanHook]] = None
```

##### on_cleanup
Задачи, выполняемые после `on_shutdown`.
```python
on_cleanup: Optional[List[LifespanHook]] = None
```

##### http_route_handlers
HTTP-роутеры, которые могут представлять собой как отдельные обработчики, так и группы `HTTPRouter`.
```python
http_route_handlers: Iterable[HTTPRouterType] = ()
```

### Атрибуты `aiohttp`
##### middlewares
Список `middleware`, применяемых ко всем обработчикам, включая дочерние приложения.
```python
middlewares: Optional[Iterable[Middleware]] = None
```

##### client_max_size
Максимальный размер запроса в байтах.
```python
client_max_size: int = 1024**2
```

##### logger
Логгер для приема логов от `Application`.
```python
logger: logging.Logger = logging.getLogger("aiohttp.web")
```

## Запуск приложения
### Простой запуск
Скопируйте в файл `main.py`.
```Python hl_lines="12"
{!> ./docs/docs/server/application/08_runserver/run_app.py !}
```
Запустите сервер:
```bash
{!> ./docs/docs/server/application/08_runserver/run_app.sh !}
```
!!! note "Можно указать параметры, например, `host` или `port`."
    ```python
    {!> ./docs/docs/server/application/08_runserver/run_app_change_host_and_port.py !}
    ```

### WSGI запуск (Gunicorn)
Установите `gunicorn`:
```bash
pip install gunicorn
```
Скопируйте код в `main.py`:
```Python
{!> ./docs/docs/server/application/08_runserver/gunicorn.py !}
```
Запустите сервер:
```shell
{!> ./docs/docs/server/application/08_runserver/gunicorn.sh !}
```

Команда `gunicorn main:app` обращается к:

* `main`: файл `main.py` (модуль Python).
* `rapidy`: объект, созданный внутри файла `main.py` в строке `rapidy = Rapidy()`.
* `--reload`: перезапускает сервер после изменения кода. Используйте только для разработки.
