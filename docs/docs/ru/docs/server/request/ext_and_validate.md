# Extraction and validation

## Извлечение и проверка данных
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
Подробнее про способы аннотации параметров можно прочитать **[здесь](../annotation)**.

```python
async def handler(
    host: str = web.Header(alias='Host')
    # or
    host: Annotated[str, web.Header(alias='Host')]
)
```
    
