# Multipart Form Data

**multipart/form-data** - один из наиболее часто используемых типов содержимого для отправки двоичных данных на сервер. 
Multipart означает, что данные отправляются на сервер отдельными частями. 
Каждый из компонентов может иметь свой тип содержимого, имя файла и данные. 
Данные отделяются друг от друга граничной строкой. 
Curl отправляет многокомпонентный запрос со специально отформатированным телом сообщения POST в виде серии «частей», 
разделенных границами MIME.


```Python
from pydantic import BaseModel
from rapidy.enums import ContentType

class UserData(BaseModel):
    username: str
    password: str

@routes.post('/')
async def handler(
    user_data: UserData = web.Body(content_type=ContentType.m_part_form_data),
    # or 
    user_data: UserData = web.Body(content_type='multipart/form-data'),
) -> ...:
```

??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: multipart/form-data" \
    -F username=User \
    -F password=myAwesomePass \
    http://127.0.0.1:8080
    ```

    !!! example ""
        ```text
        POST /  HTTP/1.1
        Host: localhost:8080
        Content-Type: multipart/form-data; boundary=---WD9146A
        Content-Length: ...

        ---WD9146A
        Content-Disposition: form-data; name="username"
        
        User
        ---WD9146A
        Content-Disposition: form-data; name="password"
        
        myAwesomePass
        ---WD9146A
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
            user_data: bytes = web.Body(content_type=ContentType.m_part_form_data),
            # also you can use pydantic validation
            user_data: bytes = web.Body(content_type=ContentType.m_part_form_data, min_length=1),
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
            user_data: web.StreamReader = web.Body(content_type=ContentType.m_part_form_data),
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
