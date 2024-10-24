# Binary
## Описание
**Binary** (mime-type: `application/octet-stream`) — двоичный тип данных. 

!!! info "`Rapidy` позволяет извлекать абсолютно любой `content_type` как последовательность байт."
    Просто укажите аннотацию как `bytes` или `StreamReader`
    
    !!! tip ""
        Может быть полезно для явного ограничения типа принимаемых данных, чтобы затем прочитать их в двоичном виде.
    

Всего существует два типа данных, которые могут использовать аннотацию для извлечения данных игнорируя ожидаемый 
`content_type`, это `bytes` и `StreamReader`.

## bytes
```python
@routes.post('/')
async def handler(
    user_data: bytes = web.Body(),
    # or use any content_type
    user_data: bytes = web.Body(content_type=ContentType.stream),
    # also you can use pydantic validation
    user_data: bytes = web.Body(min_length=1),
) -> ...:
```

## StreamReader
!!! note "Подробнее об объекте `StreamReader` можно узнать **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">здесь</a>**."

```python
from rapidy import StreamReader

@routes.post('/')
async def handler(
    user_data: StreamReader = web.Body(),
) -> ...:
```

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."
!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp`."
    - `Body(content_type=ContentType.text_plain)` - `bytes`
!!! warning "Валидация `pydantic` для `StreamReader` не работает."

!!! info "Прямое отключение валидации"
    Установите параметру `Body` аттрибут `validate=False`
    ```python
    @routes.post('/')
    async def handler(
        data: SomeBytesType = web.Body(validate=False, content_type=ContentType.stream),
    ) -> ...:
    ```

!!! info "Отключение с использованием `Any`"
    ```python
    @routes.post('/')
    async def handler(
        data: Any = web.Body(content_type=ContentType.stream),
    ) -> ...:
    ```

!!! info "Не используйте типипизацию"
    Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
    ```python
    @routes.post('/')
    async def handler(
        data = web.Body(content_type=ContentType.stream),
    ) -> ...:
    ```

## Значения по умолчанию
Если не будет передано тело http-запроса значение по умолчанию *(если оно есть)* будет подставлено в аттрибут.

!!! example "Значение по умолчанию присутствует"
    ```python
    @routes.post('/')
    async def handler(
        data: bytes = web.Body(b'some_bytes', content_type=ContentType.stream),
        # or
        data: bytes = web.Body(default_factory=lambda: b'some_bytes', content_type=ContentType.stream),
    ) -> ...:
    ```

!!! example "Опциональное тело запроса"
    ```python
    @routes.post('/')
    async def handler(
        data: bytes | None = web.Body(content_type=ContentType.stream),
        # or
        data: Optional[bytes] = web.Body(content_type=ContentType.stream),
        # or 
        data: Union[bytes, None] = web.Body(content_type=ContentType.stream),
    ) -> ...:
    ```

??? warning "Невозможно задать значение по-умолчанию для `StreamReader`."
    При попытке установить значение по умолчанию для `Body` с аннотацией `StreamReader` через `default` или 
    `default_factory` будет поднята ошибка `ParameterCannotUseDefaultError`.
    ```python
    from rapidy import StreamReader

    @routes.post('/')
    async def handler(
        user_data: StreamReader = web.Body(),
    ) -> ...:
    ```  
    ```text
    ------------------------------
    Handler attribute with Type `Body` cannot have a default value.

    Handler path: `<full_path>/main.py`
    Handler name: `handler`
    Attribute name: `data`
    ------------------------------
    ```

## Как извлекаются сырые данные
!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

### bytes
`Rapidy` внутри себя использует вызов `read` объекта `Request`, а затем передает полученный объект на валидацию 
в `pydantic` модель.

!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_body_bytes(request: Request) -> Optional[bytes]:
        if not request.body_exists:
            return None
    
        return await request.read()
    ```

### StreamReader
`Rapidy` внутри себя использует вызов `content` объекта `Request`, полученный объект будет сразу проброшен в обработчик
запроса, пропуская валидацию `pydantic`.

!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_body_stream(request: Request) -> Optional[StreamReader]:
        if not request.body_exists:
            return None
    
        return request.content
    ```
