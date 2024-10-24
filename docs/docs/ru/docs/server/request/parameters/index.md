# Parameters
## Основы извлечения и валидации данных
Для проверки и извлечения данных входящего http-запроса **Rapidy** использует свои внутренние типы данных - 
**rapidy-параметры**.

Пример извлекает и проверяет **переменную динамического пути** `user_id` и **заголовок** `Host`.
```Python
@routes.get('/{user_id}')
async def handler(
    user_id: int = web.PathParam(),
    host: str = web.Header(alias='Host'),
) -> ...:
```

**Rapidy-параметр** - это `мета-объект`, который предоставляет информацию о том как именно будут извлекаться параметры
входящего `http-запроса`.

Все **rapidy-параметры** находятся в модуле `request_parameters`.
```python
from rapidy.request_parameters import Header, Cookie, QueryParam, ..., Body
...
async def handler(user_id: int = QueryParam()) -> ...:
```

Также доступ к ним можно получить из модуля `web`.
```python
from rapidy import web
...
async def handler(user_id: int = web.QueryParam()) -> ...:
```

Информацию о каждом типе параметра, можно найти отдельно в разделе `Parameters`:

- **[Path](../parameters/path)** - *параметры пути (используются для создания динамических API)*
- **[Headers](../parameters/headers)** - *параметры входящих заголовков*
- **[Cookies](../parameters/cookies)** - *параметры входящих cookie (автоматически извлекаются из заголовков)*
- **[Query Parameters](../parameters/query)** - *параметры запроса находящиеся в URL*
- **[Body](../parameters/body)** - *параметры тела запроса*

Для извлечения данных используется `имя аттрибута` или `alias` **rapidy-параметра**.

!!! example "Извлечение с использованием имени аттрибута"
    ```python
    async def handler(test_query_param_name: int = web.QueryParam() -> int:
        return test_query_param_name
    ```

    ```bash
    curl -G -v -d "test_query_param_name=123456789" http://127.0.0.1:8080
    < HTTP/1.1 200 OK ... 
    123456789
    ```

!!! example "Извлечение с использованием `alias`"
    ```python
    async def handler(test_query_param_name: int = web.QueryParam(alias='TestQueryParamName')) -> int:
        return test_query_param_name
    ```

    ```bash
    curl -G -v -d "TestQueryParamName=123456789" http://127.0.0.1:8080
    < HTTP/1.1 200 OK ... 
    123456789
    ```

## Возможности валидации
Каждый **rapidy-параметр** является наследником 
**<a href="https://docs.pydantic.dev/latest/concepts/fields/" target="_blank">pydantic.Field</a>** 
и поддерживает все его возможности.

```Python
@routes.get('/')
async def handler(
    positive: int = web.QueryParam(gt=0),
    non_negative: int = web.QueryParam(ge=0),
    negative: int = web.QueryParam(lt=0),
    non_positive: int = web.QueryParam(le=0),
    even: int = web.QueryParam(multiple_of=2),
    love_for_pydantic: float = web.QueryParam(allow_inf_nan=True),
    short: str = web.QueryParam(min_length=3),
    long: str = web.QueryParam(max_length=10),
    regex: str = web.QueryParam(pattern=r'^\d*$'),
    precise: Decimal = web.QueryParam(max_digits=5, decimal_places=2),
) -> ...:
```

## Способы аннотации параметров
### Параметр, как значение по умолчанию

Этот способ определения является самым простым и понятным.

```Python
@routes.get('/{user_id}')
async def handler(
    user_id: int = web.PathParam(),
) -> ...:
```

Но, если вы пользуетесь статистическими анализаторами кода (такими как `mypy`), у вас могут возникнуть проблемы, 
при статической проверке вашего кода:
```
main.py:4: error: Incompatible default for argument "user_id" (default has type "PathParam", argument has type
"int")  [assignment]
```
Для того, чтобы этого избежать включите mypy-плагин для rapidy.
```toml
# pyproject.toml
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"     # <-- enable rapidy plugin
]
```

!!! note "Параметры поддерживают значения по умолчанию"
    `web.Header(default=..., default_factory=...)`

    Подробнее можно прочитать **[здесь](../default)**.


### Аннотация с помощью `typing.Annotated`

Про тип `typing.Annotated` можно прочитать в официальной документации `Python` 
**<a href="https://docs.python.org/3/library/typing.html#typing.Annotated" target="_blank">здесь</a>**.

```Python
@routes.get('/{user_id}')
async def handler(
    user_id: Annotated[int, web.PathParam()],
) -> ...:
```
```

<span class="base-color">Первый</span> аргумент **Annotated[<span class="success-color">str</span>, ...]** 
обозначает тип, который будет использоваться для валидации входных данных.
В данном случае, сервер ожидает тип данных <span class="success-color">str</span>.

<span class="base-color">Второй</span> аргумент **Annotated[..., <span class="success-color">web.Header(alias="Host")</span>]** 
всегда должен быть инстансом одного из http-параметров Rapidy (web.Header, web.Headers, web.Cookie, ..., web.Body). 
В данном случае, сервер ожидает получение заголовка `Host`.

Если второй аргумент не является http-параметром Rapidy, например, <br/>`Annotated[str, str]`, то он просто будет пропущен.

??? note "Дополнительная мета-информация в Annotated"
    Иногда для мета-программирования, есть необходимость пробросить еще какую-информацию в параметр.
    Rapidy позволяет это сделать:
    `Annotated[str, <rapidy_param>, MetaInfo1, SomeMetaInfo2, ...]`.

    В 99.9% функция бесполезна, но она есть.

!!! note "Параметры поддерживают значения по умолчанию"
    `web.Header(default=..., default_factory=...)`

    Об особенностях работы значений по умолчанию, можно прочитать в соответствующем разделе каждого параметра.

