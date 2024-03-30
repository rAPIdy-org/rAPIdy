# Extraction and validation

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
Подробнее про способы аннотации параметров можно прочитать **[здесь](../annotation)**.

```python
async def handler(
    host: str = web.Header(alias='Host')
    # or
    host: Annotated[str, web.Header(alias='Host')]
)
```

## Низкоуровневое описание работы
Работа с входными данными в `Rapidy` происходит в два этапа 
<span class="base-color">извлечение сырых данных</span> из входящего запроса и 
<span class="base-color">валидация</span> извлеченных данных в соответствии с аннотацией параметра.

??? note "Что такое аннотация"
    ```python
    async def handler(body_data: str = web.Body()) -> ...:
    ```

    - `str` - аннотация параметра
    - `web.Body()` - Rapidy-параметр
    

### Извлечение данных
Перед тем как проверить данные в соответствии с аннотацией, вначале эти данные нужно извлечь.

!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

#### Извлечение path-параметров
Для извлечения сырых данных динамического маршрута используется `match_info` метод объекта `Request`.

??? note "Как `Rapidy` извлекает path-параметры"
    ```python
    async def extract_path(request: Request) -> dict[str, str]:
        return dict(request.match_info)
    ```

#### Извлечение заголовков
Для извлечения сырых данных заголовков используется `headers` метод объекта `Request`.
??? note "Как `Rapidy` извлекает заголовки"
    ```python
    async def extract_headers(request: Request) -> MultiMapping[str]:
        return request.headers
    ```

#### Извлечение cookies
Для извлечения сырых данных cookie используется `cookies` метод объекта `Request`.
??? note "Как `Rapidy` извлекает cookies"
    ```python
    async def extract_cookies(request: Request) -> Mapping[str, str]:
        return request.cookies
    ```

#### Извлечение query-параметров
Для извлечения сырых данных заголовков используется `rel_url.query` метод объекта `Request`.
??? note "Как `Rapidy` извлекает query-параметры"
    ```python
    async def extract_query(request: Request) -> MultiDict[str]:
        return request.rel_url.query
    ```

#### Извлечение body
##### Способы извлечения данных тела запроса

###### Json
??? note "Как `Rapidy` извлекает тело запроса в качестве `json`"
    ```python
    async def extract_body_json(request: Request) -> Optional[dict[str, any]]:
        if not request.body_exists:
            return None
    
        return await request.json(...)
    ```

###### X-WWW-Form-Urlencoded
??? note "Как `Rapidy` извлекает тело запроса в качестве `x-www-form-urlencoded`"
    ```python
    async def extract_post_data(request: Request) -> Optional[MultiDictProxy[Union[str, bytes, FileField]]]:
        if not request.body_exists:
            return None
    
        return await request.post()
    ```

###### Multipart Form Data
!!! note ""
    Извлечение данных для x-www-form-urlencoded и multipart/form-data происходит одинаково, через метод `post` объекта 
    `web.Request` -> это особенность реализации `aiohttp`.

###### Text
??? note "Как `Rapidy` извлекает тело запроса в качестве `текста`"
    ```python
    async def extract_body_text(request: Request) -> Optional[str]:
        if not request.body_exists:
            return None
    
        return await request.text()
    ```

###### Binary
??? note "Как `Rapidy` извлекает тело запроса в качестве последовательности `байт`"
    ```python
    async def extract_body_bytes(request: Request) -> Optional[bytes]:
        if not request.body_exists:
            return None
    
        return await request.read()
    ```

###### StreamReader
Экстрактор необходим, когда нужно читать данные прямо из потока входящего http-запроса.
??? note "Как `Rapidy` извлекает `StreamReader`"
    ```python
    async def extract_body_stream(request: Request, body_field_info: Body) -> Optional[StreamReader]:
    if not request.body_exists:
        return None

    return request.content
    ```


##### Выбор способа извлечения данных
При выборе способа извлечения данных из запроса используется аннотация аттрибута обработчика и аттрибут `content_type` 
Rapidy-параметра.
??? note "Что такое аннотация и как определить `content_type`"
    ```python
    async def handler(body_data: str = web.Body(content_type='application/json')) -> ...:
    ```

    - `str` - аннотация параметра
    - `content_type` - аттрибут определяющий какой именно тип данных ожидает сервер

    Также `content_type` можно передать с помощью встроенного enum `rapidy.enums.ContentType`
    ```python
    async def handler(body_data: str = web.Body(content_type=ContentType.json)) -> ...:
    ```

Вначале `Rapidy` попытается найти экстрактор по типу аннотации обработчика:

- str, int, float, Decimal, Enum - данные будут извлечены как текст, с использованием [Text Extractor](#text).
!!! example "Примеры"

    - `str`
        
        Данные будут извлечены как `str` и `pydantiс` произведет валидацию строки по аттрибутам `pydantic.Field` 
        *- если они были переданы* 
        ```python
        @routes.post('/')
        async def handler(
            string_data: str = web.Body(),
            # or use a validation
            validated_string_data: str = web.Body(min_length=1),
        ) -> ...:
        ```
    
    - `int/float/Decimal`

        Данные будут извлечены как `str`, а затем `pydantic` проверит, что данные можно преобразовать к `int/float/Decimal`. 
        ```python
        @routes.post('/')
        async def handler(
            int_data: int = web.Body(),
            # or
            float_data: float = web.Body(),
            # or
            decimal_data: Decimal = web.Body(),
            # also you can use validation
            validated_data: int = web.Body(ge=1),
        ) -> ...:
        ```
    
    - `Enum`
    
        Тип имеет ряд особенностей при работе с ним, поэтому он вынесен в отдельный блок.
        
        ??? example "Отправка с помощью `curl` для примеров ниже"
            ```bash
            curl -X POST \
            -H "Content-Type: application/json" \
            -d '123' \
            http://127.0.0.1:8080
            ```
        
        Обработчик для примеров ниже:
        ```python
        @routes.post('/')
        async def handler(
             enum_data: TestEnum = web.Body(),
        ) -> None:
        ```

        Работающие примеры enum:
        ```python
        class TestEnum(Enum):
            test = '123'
      
        class TestEnum(str, Enum):
            test = '123'
        
        class TestEnum(IntEnum):
            test = 123
        ```
        
        Неработающие примеры enum:
        ```python
        class TestEnum(Enum):
            test = 123

        # {"errors": [{"type": "enum", "loc": ["body"], "msg": "Input should be 123"}]
        ```
        Этот пример не будет работать, поскольку `pydantic` не поймет как именно нужно преобразовать строковый тип.
  
- bytes - данные будут извлечены как байты, с использованием [Bytes Extractor](#binary)
!!! example "Примеры"
```python
@routes.post('/')
async def handler(
    string_data: str = web.Body(),
    # or use a validation
    validated_string_data: str = web.Body(min_length=1),
) -> ...:
```
# TODO: остановился тут







- StreamReader - данные будут извлечены как объект StreamReader с использованием 
[Stream Reader Extractor](#streamreader). *Валидация pydantic будет пропущена.*



Если `Rapidy` не смогла сопоставить текущую аннотацию аттрибута body с доступными типами, она выберет экстрактор исходя
из ожидаемого content_type
- application/json - request.json
- x-www-form-urlencoded / multipart/form-data - request.post
- text/* - request.text (text/plain, text/html, ...)

Если тип не будет найден, будет использоваться request.read и данные будут извлечены как байты.
