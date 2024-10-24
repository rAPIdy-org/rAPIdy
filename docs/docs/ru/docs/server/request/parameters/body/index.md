# Body
## Описание
**HTTP тело запроса** является частью сообщения запроса, переносящего данные от клиента к серверу. 
Это имеет решающее значение для таких методов, как POST, PUT и PATCH, используемых для создания, обновления или 
изменения ресурсов. 

Например, в запросе POST для создания учетной записи пользователя данные пользователя находятся в теле запроса.

```Python
from pydantic import BaseModel

class UserData(BaseModel):
    username: str
    password: str

@routes.post('/')
async def handler(
    user_data: UserData = web.Body(),
) -> ...:
```

Данный раздел покажет, как можно извлекать и проверять body используя **`Rapidy`**.

!!! tip "Более детальные сценарии применения вы найдете в примерах - **[Examples](../../../../../examples.md)**."

## Аттрибуты Body
### content_type
```python
# `application/json` by default
content_type: Union[str, ContentType] = ContentType.json
```
Аттрибут указывает какой тип данных в body ожидает сервер.

!!! tip "Подробнее про enum `ContentType` можно прочитать **[здесь](../../../../enums/index.md)**"

`Rapidy` будет использовать ожидаемый `content_type` для извлечения данных.

!!! info "Основные поддерживаемые типы" 

    - application/json
    - application/x-www-form-urlencoded
    - multipart/form-data
    - text/* - любой mime-type с типом текст
    - application/octet-stream
    
    !!! warning ""
        Если сервер ожидает тип, который `Rapidy` не поддерживает явно, например `video/mpeg`, то данные
        будут извлечены как `bytes` и в таком виде будут переданы в модель `pydantic` для валидации.


### check_content_type
Аттрибут указывает нужно ли проверять значение заголовка `Content-Type`.

При `True` *(значение по умолчанию)* будет выполнена проверка заголовка `Content-Type`, который присылает клиент, и 
если он не совпадает с ожидаемым `content_type`, то клиенту будет возвращена ошибка:
```json
{
    "errors": [
        {
            "type": "ExtractError",
            "loc": [
                "body"
            ],
            "msg": "Failed to extract body data: Expected Content-Type `text/plain` not `<current_request_content_type>`"
        }
    ]
}
```

### json_decoder
Аттрибут позволяет определить пользовательский `json_decoder` для извлечения данных из тела запроса.

!!! note "Аттрибут будет работать только для `content_type="application/json"`."

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

## Извлечение без валидации
Практически все типы `Body` поддерживают извлечение данных без валидации.

!!! note "Эти способы не являются рекомендованными."
!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp` для этого тела http."
!!! note "Более подробно вы можете прочитать об этом в разделе **Извлечение без валидации** любого из body-параметров."

!!! info "Прямое отключение валидации"
    Установите параметру `Body` аттрибут `validate=False`
    ```python
    from pydantic import BaseModel
        
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData = web.Body(validate=False),
    ) -> ...:
    ```

!!! info "Отключение с использованием `Any`"
    ```python
    @routes.post('/')
    async def handler(
        data: Any = web.Body(),
    ) -> ...:
    ```

!!! info "Не используйте типипизацию"
    Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
    ```python
    @routes.post('/')
    async def handler(
        data = web.Body(),
    ) -> ...:
    ```

## Значения по умолчанию
Практически все типы `Body` поддерживают значения по умолчанию.

Если не будет передано тело http-запроса значение по умолчанию *(если оно есть)* будет подставлено в аттрибут.

!!! example "Значение по умолчанию присутствует"
    ```python
    from pydantic import BaseModel
    
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData = web.Body('some_data'),
        # or
        data: BodyData = web.Body(default_factory=lambda: 'some_data'),
    ) -> ...:
    ```

!!! example "Опциональное тело запроса"
    ```python
    from pydantic import BaseModel
    
    class BodyData(BaseModel):
        ...
    
    @routes.post('/')
    async def handler(
        data: BodyData | None = web.Body(),
        # or
        data: Optional[BodyData] = web.Body(),
        # or 
        data: Union[BodyData, None] = web.Body(),
    ) -> ...:
    ```

!!! note "Более подробно вы можете прочитать об этом в разделе **Значения по умолчанию** любого из body-параметров."
