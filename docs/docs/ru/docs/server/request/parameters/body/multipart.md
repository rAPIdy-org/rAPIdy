# Multipart Form Data
## Описание
**Form Data** *(mime-type: `multipart/form-data`)* - один из наиболее часто используемых типов содержимого 
для отправки **двоичных** данных на сервер. 

Multipart означает, что данные отправляются на сервер отдельными частями. 
Каждый из компонентов может иметь свой тип содержимого, имя файла и данные. 
Данные отделяются друг от друга граничной строкой. 

```Python
from pydantic import BaseModel, ConfigDict
from rapidy.enums import ContentType

class UserData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    username: str
    password: str
    image: FileField

@routes.post('/')
async def handler(
    user_data: UserData = web.Body(content_type=ContentType.m_part_form_data),
    # or 
    user_data: UserData = web.Body(content_type='multipart/form-data'),
) -> ...:
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
    Content-Disposition: form-data; name="image"; filename="image.png";
    Content-Type: image/png

    <... binary data ...>
    ---WD9146A
    ```

??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: multipart/form-data" \
    -F username=User \
    -F password=myAwesomePass \
    http://127.0.0.1:8080
    ```

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."
!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp`."
    - `Body(content_type=ContentType.m_part_form_data)` - `MultiDictProxy[Union[str, bytes, FileField]]`

!!! info "Прямое отключение валидации"
    Установите параметру `Body` аттрибут `validate=False`
    ```python
    from pydantic import BaseModel
        
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData = web.Body(validate=False, content_type=ContentType.m_part_form_data),
    ) -> ...:
    ```

!!! info "Отключение с использованием `Any`"
    ```python
    @routes.post('/')
    async def handler(
        data: Any = web.Body(content_type=ContentType.m_part_form_data),
    ) -> ...:
    ```

!!! info "Не используйте типипизацию"
    Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
    ```python
    @routes.post('/')
    async def handler(
        data = web.Body(content_type=ContentType.m_part_form_data),
    ) -> ...:
    ```

## Значения по умолчанию
Если не будет передано тело http-запроса значение по умолчанию *(если оно есть)* будет подставлено в аттрибут.

!!! example "Значение по умолчанию присутствует"
    ```python
    from pydantic import BaseModel
    
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData = web.Body('some_data', content_type=ContentType.m_part_form_data),
        # or
        data: BodyData = web.Body(default_factory=lambda: 'some_data', content_type=ContentType.m_part_form_data),
    ) -> ...:
    ```

!!! example "Опциональное тело запроса"
    ```python
    from pydantic import BaseModel
    
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData | None = web.Body(content_type=ContentType.m_part_form_data),
        # or
        data: Optional[BodyData] = web.Body(content_type=ContentType.m_part_form_data),
        # or 
        data: Union[BodyData, None] = web.Body(content_type=ContentType.m_part_form_data),
    ) -> ...:
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
        from rapidy import StreamReader

        @routes.post('/')
        async def handler(
            user_data: StreamReader = web.Body(content_type=ContentType.m_part_form_data),
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
            user_data: StreamReader = web.Body(content_type=ContentType.m_part_form_data),
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