# Text
## Описание
**Text** *(mime-type: `text/*`)* — тип данных представляющий собой строку.

!!! info "`Rapidy` будет работать с любым текстом независимо от его `subtype`."
    Например: `text/plain`, `text/html`, `text/css`, `text/xml`, `...`, `text/*`.

!!! info ""
    Для декодирования текста будет использоваться параметр `charset` заголовка <br/>`Content-Type`.
    Если `charset` не определен клиентом, текст будет декодирован с помощью `utf-8`.

```Python
from rapidy.enums import ContentType

@routes.post('/')
async def handler(
    text_data: str = web.Body(content_type=ContentType.text_plain),
    # or 
    text_data: str = web.Body(content_type=ContentType.text_html),
    # or any mime-type with type `text`
    text_data: str = web.Body(content_type=ContentType.text_any),
) -> ...:
```

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."
!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp`."
    - `Body(content_type=ContentType.text_plain)` - `str`

!!! info "Прямое отключение валидации"
    Установите параметру `Body` аттрибут `validate=False`
    ```python
    class DataEnum(Enum):
        test = 'test'
    
    @routes.post('/')
    async def handler(
        data: DataEnum = web.Body(validate=False, content_type=ContentType.text_plain),
    ) -> ...:
    ```

!!! info "Отключение с использованием `Any`"
    ```python
    @routes.post('/')
    async def handler(
        data: Any = web.Body(content_type=ContentType.text_plain),
    ) -> ...:
    ```

!!! info "Не используйте типипизацию"
    Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
    ```python
    @routes.post('/')
    async def handler(
        data = web.Body(content_type=ContentType.text_plain),
    ) -> ...:
    ```

## Значения по умолчанию
Если не будет передано тело http-запроса значение по умолчанию *(если оно есть)* будет подставлено в аттрибут.

!!! example "Значение по умолчанию присутствует"
    ```python
    class DataEnum(Enum):
        test = 'test'
    
    @routes.post('/')
    async def handler(
        data: DataEnum = web.Body('some_data', content_type=ContentType.text_plain),
        # or
        data: DataEnum = web.Body(default_factory=lambda: 'some_data', content_type=ContentType.text_plain),
    ) -> ...:
    ```

!!! example "Опциональное тело запроса"
    ```python
    class DataEnum(Enum):
        test = 'test'

    @routes.post('/')
    async def handler(
        data: DataEnum | None = web.Body(content_type=ContentType.text_plain),
        # or
        data: Optional[DataEnum] = web.Body(content_type=ContentType.text_plain),
        # or 
        data: Union[DataEnum, None] = web.Body(content_type=ContentType.text_plain),
    ) -> ...:
    ```

## Как извлекаются сырые данные
`Rapidy` внутри себя использует вызов `text` объекта `Request`, а затем передает полученный объект на валидацию 
в `pydantic` модель.


!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_body_text(request: Request) -> Optional[str]:
        if not request.body_exists:
            return None
    
        return await request.text()
    ```

!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

Однако, если аннотация определена как `bytes` или `StreamReader`, то данные будут извлекаться иначе:

!!! note "Подробнее об объекте `StreamReader` можно узнать **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">здесь</a>**."

- bytes

    !!! example "Пример обработчика"
        ```python
        @routes.post('/')
        async def handler(
            user_data: bytes = web.Body(content_type=ContentType.text_plain),
            # also you can use pydantic validation
            user_data: bytes = web.Body(content_type=ContentType.text_plain, min_length=1),
        ) -> ...:
        ```
    !!! info "Код `Rapidy`"
        ```python
        async def extract_body_bytes(request: Request) -> Optional[bytes]:
            if not request.body_exists:
                return None
        
            return await request.read()
        ```

- StreamReader

    !!! example "Пример обработчика"
        ```python
        from rapidy import StreamReader

        @routes.post('/')
        async def handler(
            user_data: StreamReader = web.Body(content_type=ContentType.text_plain),
        ) -> ...:
        ```
    !!! info "Код `Rapidy`"
        ```python
        async def extract_body_stream(request: Request) -> Optional[StreamReader]:
            if not request.body_exists:
                return None

            return request.content
        ```
    !!! warning "Валидация `pydantic` для `StreamReader` не будет работать."
    ??? warning "Невозможно задать значение по-умолчанию для `StreamReader`."
        При попытке установить значение по умолчанию для `Body` с аннотацией `StreamReader` через `default` или 
        `default_factory` будет поднята ошибка `ParameterCannotUseDefaultError`.
        ```python
        from rapidy import StreamReader

        @routes.post('/')
        async def handler(
            user_data: StreamReader = web.Body(content_type=ContentType.text_plain),
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
