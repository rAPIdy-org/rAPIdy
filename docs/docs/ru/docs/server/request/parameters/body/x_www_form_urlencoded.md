# X-WWW-Form-Urlencoded
## Описание
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

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."
!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp`."
    - `Body(content_type=ContentType.x_www_form)` - `MultiDictProxy[str]`

!!! info "Прямое отключение валидации"
    Установите параметру `Body` аттрибут `validate=False`
    ```python
    from pydantic import BaseModel
        
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData = web.Body(validate=False, content_type=ContentType.x_www_form),
    ) -> ...:
    ```

!!! info "Отключение с использованием `Any`"
    ```python
    @routes.post('/')
    async def handler(
        data: Any = web.Body(content_type=ContentType.x_www_form),
    ) -> ...:
    ```

!!! info "Не используйте типипизацию"
    Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
    ```python
    @routes.post('/')
    async def handler(
        data = web.Body(content_type=ContentType.x_www_form),
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
        data: BodyData = web.Body('some_data', content_type=ContentType.x_www_form),
        # or
        data: BodyData = web.Body(default_factory=lambda: 'some_data', content_type=ContentType.x_www_form),
    ) -> ...:
    ```

!!! example "Опциональное тело запроса"
    ```python
    from pydantic import BaseModel
    
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData | None = web.Body(content_type=ContentType.x_www_form),
        # or
        data: Optional[BodyData] = web.Body(content_type=ContentType.x_www_form),
        # or 
        data: Union[BodyData, None] = web.Body(content_type=ContentType.x_www_form),
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
    ??? warning "Невозможно задать значение по-умолчанию для `StreamReader`."
        При попытке установить значение по умолчанию для `Body` с аннотацией `StreamReader` через `default` или 
        `default_factory` будет поднята ошибка `ParameterCannotUseDefaultError`.
        ```python
        from rapidy import StreamReader

        @routes.post('/')
        async def handler(
            user_data: StreamReader = web.Body(content_type=ContentType.x_www_form),
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