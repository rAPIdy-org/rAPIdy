# Маршрутизация и создание HTTP-обработчиков
Веб-обработчики (handlers) предназначены для обработки входящих HTTP-запросов.

В `Rapidy` маршрутизация и создание обработчиков тесно связаны: маршрутизация определяет, какой обработчик будет вызван в ответ на запрос.

## Определение маршрутов
Маршрут — это строка `URL`, по которой вызывается обработчик.

Всего существуют два вида маршрутов - статические и динамические.

!!! info "Разница между статическим и динамическим роутингом"
    | Тип маршрута | Пример URL       | Описание |
    | ------------ | ---------------- | -------- |
    | Статический  | /about           | URL фиксирован.                          |
    | Динамический | /users/{user_id} | URL меняется в зависимости от параметров |


!!! info ""
    `Rapidy` поддерживает несколько способов определения маршрутов, аналогичных `aiohttp`, подробнее о них ниже в разделе `Создание и регистрация обработчиков
    HTTP-запросов`.

    Подробнее про обработчики `aiohttp` можно узнать **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

---

### Статические маршруты
Статический HTTP-роутинг — это маршрутизация, где путь (URL) заранее известен и не меняется динамически.
Это означает, что каждый запрос с определённым маршрутом всегда приводит к одному и тому же обработчику.

**Простой статический маршрут**
```python hl_lines="3"
from rapidy.http import get

@get('/hello_rapidy')
async def handler() -> str:
    return 'Hello Rapidy!'
```

!!! info "Этот маршрут всегда доступен по `GET /hello` и возвращает один и тот же ответ."
    ```shell
    curl http://localhost:8000/hello_rapidy
    ```

Таким же образом вы можете определять и другие методы, такие как `get`, `post`, `put`, `delete` и так далее.

### Динамические маршруты
Динамический роутинг позволяет задавать маршруты, которые принимают переменные параметры.
Это полезно, когда нужно работать с различными сущностями (например, `user_id`, `post_id` и т.д.), передавая их в `URL`.

!!! info "В примерах ниже будет использоваться `PathParam`, который необходим для извлечения параметров-путей. Подробнее о нем можно прочитать [здесь](../request/parameters/path)."

#### Простой динамический маршрут

Допустим, у нас есть API для получения информации о пользователе по его user_id:

```python hl_lines="3"
from rapidy.http import get, PathParam

@get('/users/{user_id}')
async def handler(user_id: int = PathParam()) -> dict[str, int]:
    return {'user_id': user_id}
```

Как работает этот маршрут?

1. `user_id` — динамический параметр, который передаётся в URL.
2. `Rapidy` автоматически преобразует его в `int` (если передать строку, API вернёт ошибку `422`).

Пример запроса:
```shell
curl http://localhost:8000/users/123
```

Ответ:
```text
{"user_id": 123}
```

#### Динамические маршруты с несколькими параметрами

Можно добавить несколько динамических параметров:
```python hl_lines="3"
from rapidy.http import get, PathParam

@get('/posts/{post_id}/comments/{comment_id}')
async def handler(
    post_id: int = PathParam(),
    comment_id: int = PathParam(),
) -> dict[str, int]:
    return {'post_id': post_id, 'comment_id': comment_id}
```

Теперь запрос `GET /posts/10/comments/5` вернёт:
```text
{"post_id": 10, "comment_id": 5}
```

### Группировка маршрутов
Если у вас много маршрутов, можно использовать один из подходов для группировки HTTP-запросов.

!!! note "Рекомендуется придерживаться только одного подхода в рамках проекта."

#### HTTPRouter
`Rapidy` предлагает использовать объект `HTTPRouter` для группировки запросов.

`HTTPRouter` позволяет регистрировать группы обработчиков и играет ключевую роль в маршрутизации (routing),
помогая направлять запросы к нужным обработчикам в зависимости от HTTP-метода, пути, параметров и других условий.

!!! info "HTTPRouter регистрируется точно так же, как и любой HTTP-обработчик."

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

!!! tip "`HTTPRouter` умеет больше!"
    `HTTPRouter` также имеет ряд атрибутов расширяющих его возможности, такие как обработка `middleware`, управление фоновыми задачами и тд.

    Также вы можете создавать вложенные `HTTPRouter`.

    Подробнее про `HTTPRouter` можно прочитать [здесь](http_router)

---

## Создание и регистрация обработчиков HTTP-запросов

### Функциональные обработчики

Простейший способ создания обработчика:
```Python
{!> ./docs/docs/server/handlers/01_func_handler.py !}
```

#### Примеры регистрации обработчиков

??? example "Регистрация обработчика без декоратора"
    ```Python
    {!> ./docs/docs/server/handlers/02_func_handler_no_deco.py !}
    ```

??? example "Добавление обработчика через `router` приложения _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/03_func_handler_add_method_aio_style.py !}
    ```

    !!! info "Поддерживаемые методы соответствуют HTTP-методам с префиксом `add_`."
    - `add_get`
    - `add_post`
    - `add_put`
    - `add_patch`
    - `add_delete`

    !!! note "Исключение — `view`."
        - `add_view`

??? example "Добавление обработчика с декоратором через `RouteTableDef` _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/04_func_handler_routetable_deco.py !}
    ```

??? example "Добавление обработчика без декоратора через `rapidy.web` _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/05_func_handler_app_add_routes.py !}
    ```

---

### Классовые обработчики

Классовые обработчики позволяют объединять несколько методов в одном классе:
```Python
{!> ./docs/docs/server/handlers/06_controller_handler.py !}
```

#### Примеры регистрации классовых обработчиков

??? example "Регистрация обработчика без декоратора"
    ```Python
    {!> ./docs/docs/server/handlers/07_controller_handler_no_deco.py !}
    ```

##### Использование `View` _(aiohttp style)_
??? example "Добавление обработчика через `router` приложения _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/08_view_router.py !}
    ```

??? example "Добавление обработчика через `router` с разными путями _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/09_view_router_different_path.py !}
    ```

??? example "Добавление обработчика с декоратором через `RouteTableDef` _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/10_view_routetabledef.py !}
    ```

??? example "Добавление обработчика с декоратором через `RouteTableDef` с разными путями _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/11_view_routetabledef_different_path.py !}
    ```

??? example "Добавление обработчика без декоратора через `rapidy.web` _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/12_view_add_routes.py !}
    ```

??? example "Добавление обработчика без декоратора через `rapidy.web` с разными путями _(в стиле `aiohttp`)_"
    ```Python
    {!> ./docs/docs/server/handlers/13_view_add_routes_different_path.py !}
    ```

---

## Атрибуты обработчиков
Атрибуты позволяют управлять поведением обработчиков и ответами.

Атрибуты автоматически применяются к ответам обработчиков, если обработчик возвращает что угодно кроме `Response`
_(не относится к атрибутам `path` и `allow_head` для метода `get`)_.

!!! example "Атрибуты применяются к ответам."
    Атрибут `response_content_type` будет применяться к каждому ответу обработчика,
    поскольку обработчик возвращает `python` объект.
    ```python
    from rapidy.http import get, ContentType

    @get('/', response_content_type=ContentType.text_plain)
    async def handler() -> str:
        return 'Hello Rapidy!'
    ```

!!! example "Атрибуты не применяются к ответам."
    Атрибут `response_content_type` не будет применяться к ответу обработчика,
    поскольку обработчик возвращает низкоуровневый `Response` объект.
    ```python
    from rapidy.http import get, ContentType, Response

    @get('/', response_content_type=ContentType.text_plain)
    async def handler() -> Response:
        return Response('Hello Rapidy!')
    ```

!!! info "Все способы создания обработчиков поддерживают одинаковые атрибуты для управления веб-запросом."

### Основные атрибуты (применяются всегда)
#### path
**`path`**: `str` — маршрут обработчика на сервере.
```python hl_lines="2"
{!> ./docs/docs/server/handlers/attrs/path.py !}
```

---

#### allow_head
**`allow_head`**: `bool = True` — если равен True (по умолчанию), то добавляется маршрут для метода `head` с тем же обработчиком, что и для `get`.

```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/allow_head.py !}
```

!!! note "Аттрибут может быть применен только к методу `get`."

---

### Валидация ответа

#### response_validate
**`response_validate`**: `bool = True` — проверять ли ответ обработчика.
```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/response_validate.py !}
```

---

#### response_type
**`response_type`**: `Type[Any] | None = ...` — определяет тип ответа (заменяет аннотацию возврата).
```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/response_type.py !}
```

!!! note "Этот флаг добавляет гибкость в сериализацию и валидацию, но используется редко."

---

### Управление заголовками и кодировкой

#### response_content_type
**`response_content_type`**: `str = 'application/json'` — аттрибут позволяющий управлять заголовком `Content-Type`.

Заголовок `Content-Type` сообщает клиенту (браузеру, API-клиенту, другому серверу), какой тип данных содержится в теле HTTP-ответа.

```python hl_lines="5"
{!> ./docs/docs/server/handlers/attrs/response_content_type/index.py !}
```

!!! note "Если указан `content_type`, переданные данные будут преобразованы в соответствии с ним."

!!! note "Если `content_type` не указан - `content_type` будет определен автоматически в зависимости от типа данных которое отдает сервер."

??? example "content_type="application/json"
    `content_type="application/json"` — данные преобразуются в `JSON` с использованием [jsonify(dumps=True)](../../encoders)
    и кодируются в соответствии с [response_charset](#response_charset).

    ```python hl_lines="5"
    {!> ./docs/docs/server/handlers/attrs/response_content_type/json_dict.py !}
    ```

    !!! note ""
        Если переданный объект является строкой `Response(body="string")`, то строка, согласно стандарту **JSON**, будет экранирована дважды:
        ```python hl_lines="5"
        {!> ./docs/docs/server/handlers/attrs/response_content_type/json_str.py !}
        ```

??? example "content_type="text/*"
    `content_type="text/*"` *(любой текстовый тип: `text/plain`, `text/html` и т. д.)* - если данные имеют тип `str`, они отправляются без изменений.
    В противном случае они преобразуются в строку через [jsonify(dumps=False)](../../encoders).

    ```python hl_lines="5"
    {!> ./docs/docs/server/handlers/attrs/response_content_type/text.py !}
    ```

    !!! info ""
        Если после `jsonify(dumps=False)` объект все еще не является строкой, он дополнительно преобразуется с помощью [response_json_encoder](#response_json_encoder).

??? example "content_type - любой другой MIME-type."
    Если данные имеют тип `bytes`, они отправляются без изменений.
    В противном случае они преобразуются в строку с использованием [jsonify(dumps=True)](../../encoders) и кодируются в соответствии с [response_json_encoder](#response_json_encoder).

!!! info "Если `content_type` не указан, он устанавливается автоматически:"

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
**`response_charset`**: `str = 'utf-8'` — кодировка, используемая для кодирования данных ответа.

```python hl_lines="5"
{!> ./docs/docs/server/handlers/attrs/response_charset.py !}
```

---

#### response_json_encoder
**`response_json_encoder`**: `Callable = json.dumps` — функция, принимающая объект и возвращающая его JSON-представление.

Автоматически применяется к любому python объекту после валидации его через `pydantic`.
```python hl_lines="8"
{!> ./docs/docs/server/handlers/attrs/response_json_encoder.py !}
```

---

### Сжатие данных

#### response_zlib_executor
**`response_zlib_executor`**: `concurrent.futures.Executor | None = None` — функция сжатия `zlib`.
```python hl_lines="8"
{!> ./docs/docs/server/handlers/attrs/response_zlib_executor.py !}
```
!!! note "Подробнее о `zlib_executor`"
    `zlib_executor` — механизм `aiohttp`. Подробнее **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

---

#### response_zlib_executor
**response_zlib_executor_size**: `int | None = None` — размер тела в байтах для включения сжатия.
```python hl_lines="3"
{!> ./docs/docs/server/handlers/attrs/response_zlib_executor_size.py !}
```

---

### Управление полями Pydantic

#### response_include_fields
`response_include_fields`**: `set[str] | dict[str, Any] | None = None` — параметр `include` из `Pydantic`, указывающий, какие поля включать.
```python hl_lines="9"
{!> ./docs/docs/server/handlers/attrs/response_include_fields.py !}
```

---

#### response_exclude_fields
**`response_exclude_fields`**: `set[str] | dict[str, Any] | None` — список полей для исключения.
```python hl_lines="9"
{!> ./docs/docs/server/handlers/attrs/response_exclude_fields.py !}
```

---

#### response_by_alias
**`response_by_alias`**: `bool = True` — использовать ли псевдонимы `Pydantic`.
```python hl_lines="8 17"
{!> ./docs/docs/server/handlers/attrs/response_by_alias.py !}
```

---

#### response_exclude_unset
**`response_exclude_unset`**: `bool = False` — исключать ли значения по умолчанию.
```python hl_lines="9 18"
{!> ./docs/docs/server/handlers/attrs/response_exclude_unset.py !}
```

---

#### response_exclude_defaults
**`response_exclude_defaults`**: `bool = False` — исключать ли явно заданные значения, если они совпадают с дефолтными.
```python hl_lines="8 17"
{!> ./docs/docs/server/handlers/attrs/response_exclude_defaults.py !}
```

---

#### response_exclude_none
**`response_exclude_none`**: `bool = False` — исключать ли `None`-значения.
```python hl_lines="9 18"
{!> ./docs/docs/server/handlers/attrs/response_exclude_none.py !}
```

---

#### response_custom_encoder
**`response_custom_encoder`**: `Callable | None = None` — параметр custom_encoder из `Pydantic`, позволяющий задать пользовательский кодировщик.
