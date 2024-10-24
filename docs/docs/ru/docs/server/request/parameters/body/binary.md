# Binary

Binary (mime-type: `любой`) — двоичный тип данных. 

`Rapidy` позволяет извлекать абсолютно любой `content_type` как последовательность байт.

!!! tip "Может быть полезно для явного ограничения типа принимаемых данных, чтобы затем прочитать их в двоичном виде."

Всего существует два типа данных, которые могут использовать аннотацию для извлечения данных игнорируя ожидаемый 
`content_type`, это `bytes` и `StreamReader`.

!!! note "Подробнее об объекте `StreamReader` можно узнать **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">здесь</a>**."

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
```python
from rapidy import StreamReader

@routes.post('/')
async def handler(
    user_data: StreamReader = web.Body(),
) -> ...:
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
