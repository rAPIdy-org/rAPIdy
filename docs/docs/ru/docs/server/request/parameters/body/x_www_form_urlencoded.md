# X-WWW-Form-Urlencoded

**X-WWW-Form-Urlencoded** *(mime-type: `application/x-www-form-urlencoded`)* - является распространенным типом контента, используемым при отправке данных 
через HTML-формы в Интернете.

Это способ кодирования пар ключ-значение в виде строки в формате key1=value1&key2=value2.

```Python
from pydantic import BaseModel
from rapidy.enums import ContentType

class UserData(BaseModel):
    username: str
    password: str

@routes.post('/')
async def handler(
    user_data: UserData = web.Body(content_type=ContentType.x_www_form),
    # or 
    user_data: UserData = web.Body(content_type='application/x-www-form-urlencoded'),
) -> ...:
```

??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=User&password=myAwesomePass" \
    http://127.0.0.1:8080
    ```

## Как извлекаются сырые данные
`Rapidy` внутри себя использует вызов `post` объекта `Request`, а затем передает полученный объект на валидацию 
в `pydantic` модель.

!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_post_data(request: Request) -> Optional[MultiDictProxy[Union[str, bytes, FileField]]]:
        if not request.body_exists:
            return None
    
        return await request.post()
    ```

!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

!!! note ""
    Извлечение данных для `x-www-form-urlencoded` и `multipart/form-data` происходит одинаково, через метод `post` объекта 
    `web.Request` -> это особенность реализации `aiohttp`.

Однако, если аннотация определена как `bytes` или `StreamReader`, то данные будут извлекаться иначе:

!!! note "Подробнее об объекте `StreamReader` можно узнать **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">здесь</a>**."

- bytes

    !!! example "Пример обработчика"
        ```python
        @routes.post('/')
        async def handler(
            user_data: bytes = web.Body(content_type=ContentType.x_www_form),
            # also you can use pydantic validation
            user_data: bytes = web.Body(content_type=ContentType.x_www_form, min_length=1),
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
            user_data: StreamReader = Body(content_type=ContentType.x_www_form),
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
