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

---

##### lifespan
Список фоновых задач, которые запускаются и завершаются вместе с сервером.
```python
lifespan: Optional[List[LifespanCTX]] = None
```

---

##### on_startup
Список задач, запускаемых сразу после старта приложения.
```python
on_startup: Optional[List[LifespanHook]] = None
```

---

##### on_shutdown
Задачи, выполняемые при остановке сервера.
```python
on_shutdown: Optional[List[LifespanHook]] = None
```

---

##### on_cleanup
Задачи, выполняемые после `on_shutdown`.
```python
on_cleanup: Optional[List[LifespanHook]] = None
```

---

##### http_route_handlers
HTTP-роутеры, которые могут представлять собой как отдельные обработчики, так и группы `HTTPRouter`.
```python
http_route_handlers: Iterable[HTTPRouterType] = ()
```

---

### Атрибуты DI (dishka)

В качестве движка для внедрения зависимостей Rapidy использует библиотеку Dishka.

!!! info "Подробнее о механизме работы DI и особенностях интеграции читайте [здесь](../../dependency_injection)."

---

##### di_container
Внешний DI-контейнер, который можно передать в Rapidy.

```python
di_container: AsyncContainer | None = None
```

По умолчанию Rapidy создаёт и управляет собственным контейнером.
Если вы передаёте контейнер вручную, вам нужно самостоятельно контролировать его жизненный цикл (запуск и остановку).

!!! note "Rapidy не создаст новый контейнер, даже если указаны другие DI-параметры."

!!! tip "Документация Dishka — [container](https://dishka.readthedocs.io/en/stable/container/index.html)."

---

##### di_providers
Провайдеры, которые будут зарегистрированы в контейнере.

Провайдер — это объект, члены которого используются для построения зависимостей.

```python
di_providers: Sequence[BaseProvider] = ()
```

!!! note "Параметр будет проигнорирован, если указан `di_container`."

!!! tip "Документация Dishka — [providers](https://dishka.readthedocs.io/en/stable/provider/index.html)."

---

##### di_scopes
Класс `Scope`, который будет использоваться контейнером.

```python
di_scopes: type[BaseScope] = Scope
```

!!! note "Параметр будет проигнорирован, если указан `di_container`."

!!! tip "Документация Dishka — [scopes](https://dishka.readthedocs.io/en/stable/advanced/scopes.html)."

---

##### di_context
Словарь, позволяющий передавать дополнительный контекст внутрь уже объявленных провайдеров.

```python
di_context: dict[Any, Any] | None = None
```

!!! note "Параметр будет проигнорирован, если указан `di_container`."

!!! tip "Документация Dishka — [context](https://dishka.readthedocs.io/en/stable/advanced/context.html)."

---

##### di_lock_factory
Фабрика для создания блокировок, которые будет использовать контейнер.

```python
di_lock_factory: Callable[[], contextlib.AbstractAsyncContextManager[Any]] | None = Lock
```

!!! note "Параметр будет проигнорирован, если указан `di_container`."

!!! tip "Документация Dishka — [lock_factory](https://dishka.readthedocs.io/en/stable/container/index.html)."

```python
{!> ./docs/docs/server/application/di_lock_factory.py !}
```

---

##### di_skip_validation
Флаг, определяющий необходимость пропуска валидации для провайдеров, имеющих один и тот же тип.

```python
di_skip_validation: bool = False
```

!!! note "Параметр будет проигнорирован, если указан `di_container`."

!!! tip "Документация Dishka — [skip_validation](https://dishka.readthedocs.io/en/stable/advanced/components.html)."

```python
{!> ./docs/docs/server/application/di_skip_validation.py !}
```

---

##### di_start_scope
Параметр, определяющий начальный `Scope`.

```python
di_start_scope: BaseScope | None = None
```

!!! note "Параметр будет проигнорирован, если указан `di_container`."

!!! tip "Документация Dishka — [start_scope](https://dishka.readthedocs.io/en/stable/advanced/scopes.html)."

---

##### di_validation_settings
Конфигурация для переопределения настроек валидации контейнера.

```python
di_validation_settings: ValidationSettings = DEFAULT_VALIDATION
```

!!! note "Параметр будет проигнорирован, если указан `di_container`."

!!! tip "Документация Dishka — [alias](https://dishka.readthedocs.io/en/latest/provider/alias.html)."
!!! tip "Документация Dishka — [from_context](https://dishka.readthedocs.io/en/latest/provider/from_context.html)."
!!! tip "Документация Dishka — [provide](https://dishka.readthedocs.io/en/latest/provider/provide.html)."

---

### Атрибуты `aiohttp`
##### middlewares
Список `middleware`, применяемых ко всем обработчикам, включая дочерние приложения.
```python
middlewares: Optional[Iterable[Middleware]] = None
```

---

##### client_max_size
Максимальный размер запроса в байтах.
```python
client_max_size: int = 1024**2
```

---

##### logger
Логгер для приема логов от `Application`.
```python
logger: logging.Logger = logging.getLogger("aiohttp.web")
```

---

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

---

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
