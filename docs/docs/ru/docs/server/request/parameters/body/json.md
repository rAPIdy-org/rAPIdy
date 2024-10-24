# Json

**Json** (JavaScript Object Notation) *(mime-type: `application/json`)* - текстовый формат обмена структурированными 
данными, основанный на JavaScript. Сейчас формат независим от JS и может использоваться в любом языке программирования. 

Данный раздел покажет, как можно извлекать `json` из тела запроса и проверять используя **`Rapidy`**.

!!! tip "Более детальные сценарии применения вы найдете в примерах - **[Examples](../../../../../examples.md)**."

## Типы данных в JSON
### Объект
Неупорядоченное множество пар «ключ:значение».
```
{
    "username: "User",
    "password": "myAwesomePass"
}
```
```Python
from pydantic import BaseModel
from rapidy.enums import ContentType

class UserData(BaseModel):
    username: str
    password: str

@routes.post('/')
async def handler(
    user_data: UserData = web.Body(),
    # or
    user_data: UserData = web.Body(content_type=ContentType.json),
    # or 
    user_data: UserData = web.Body(content_type='application/json'),
) -> ...:
```

??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"username": "User", "password": "myAwesomePass"}' \
    http://127.0.0.1:8080
    ```

### Массив
```
[{"username: "User1", "password": "myAwesomePass1"}, {"username: "User2", "password": "myAwesomePass2"},]
```
```python
from pydantic import BaseModel

class UserData(BaseModel):
    username: str
    password: str

@routes.post('/')
async def handler(
    users: list[UserData] = web.Body(),
) -> ...:
```
??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d '[{"username": "user1", "password": "password1"}, {"username": "user2", "password": "password2"}]' \
    http://127.0.0.1:8080
    ```

### Число
Целое или вещественное.
```
111
```
Код `Rapidy`:
```python
@routes.post('/')
async def handler(
    int_data: int = web.Body(),
) -> ...:
```
??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d '"111"' \
    http://127.0.0.1:8080
    ```
!!! note "При отправке строки как `json` потребуется дополнительное экранирование символов -> `"111"`"

### Литералы
`true` (логическое значение «истина»), `false` (логическое значение «ложь») и `null`
```
true
false
null
```
```python
@routes.post('/')
async def handler(
    bool_data: bool = web.Body(),
) -> ...:
```
??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d 'true' \
    http://127.0.0.1:8080
    ```
    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d 'false' \
    http://127.0.0.1:8080
    ```
    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d 'null' \
    http://127.0.0.1:8080
    ```

### Строка
```
SomeString
```
```python
@routes.post('/')
async def handler(
    string_data: str = web.Body(),
) -> ...:
```
??? example "Отправка с помощью `curl`"
    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d '"SomeString"' \
    http://127.0.0.1:8080
    ```
!!! note "При отправке строки как `json` потребуется дополнительное экранирование символов -> `"SomeString"`"

## Кастомный Json-decoder
По умолчанию, для декодирования входящего Json, `Rapidy` использует `json.loads` без параметров.

!!! example "Равнозначные примеры"
    ```python
    @routes.post('/')
    async def handler(
        data: str = web.Body(),
    ) -> ...:
    ```
    или
    ```python
    import json
    
    @routes.post('/')
    async def handler(
        data: str = web.Body(json_decoder=json.loads),
    ) -> ...:
    ```

Если вы хотите декодировать Json по своему, просто передайте в аттрибут `json_decoder` любой вызываемый объект,
который принимает `str`.

!!! note "Ожидаемый тип данных `Callable[[str], Any]`"

!!! example "Пример с пользовательским декодером"
    ```python
    
    def custom_json_decoder(data: str) -> ...:
        ...

    @routes.post('/')
    async def handler(
        data: Any = web.Body(json_decoder=custom_json_decoder),
    ) -> ...:
    ```

Если вы хотите использовать `json.loads` с параметрами или хотите использовать свой декодер с параметрами, воспользуйтесь
функцией `functools.partial`.
    
```python
import json
from functools import partial
from typing import Any, OrderedDict

decoder = partial(json.loads, object_pairs_hook=OrderedDict)

@routes.post('/')
async def handler(
    data: Any = web.Body(json_decoder=decoder),
) -> ...:
```

## Как извлекаются сырые данные
`Rapidy` внутри себя использует вызов `json` объекта `Request`, а затем передает полученный объект на валидацию 
в `pydantic` модель.

Если извлечь данные как `json` не удалось, будет отдана ошибка `ExtractError`.
```json
{
    "errors": [
        {
            "type": "ExtractError",
            "loc": [
                "body"
            ],
            "msg": "Failed to extract body data as Json: <error_description>"
        }
    ]
}
```

!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_body_json(request: Request, body_field_info: Body) -> Optional[DictStrAny]:
    if not request.body_exists:
        return None

    return await request.json(loads=body_field_info.json_decoder)
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
            user_data: bytes = web.Body(),
            # also you can use pydantic validation
            user_data: bytes = web.Body(min_length=1),
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
            user_data: StreamReader = web.Body(),
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
