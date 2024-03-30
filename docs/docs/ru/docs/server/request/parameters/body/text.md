# Text

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
        @routes.post('/')
        async def handler(
            user_data: web.StreamReader = web.Body(content_type=ContentType.text_plain),
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
