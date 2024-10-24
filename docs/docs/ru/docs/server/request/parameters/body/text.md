# Text

Text *(mime-type: `text/*`)* — тип данных представляющий собой строку.

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
