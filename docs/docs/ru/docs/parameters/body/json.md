# Json

## Ключевые особенности

JsonEncoder - кто принимает?
На текущий момент это техническое ограничение - будет доработано в будущих обновлениях.

## Аттрибуты

* body_max_size
* json_decoder

## Типы данных

### JsonBody
<details open>
<summary><code>JsonBody</code></summary>

```Python hl_lines="6"
from rapidy.request_params import JsonBody

@routes.get('/')
async def handler(
        request: web.Request,
        username: Annotated[str, JsonBody],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

<details>
<summary>Расширенный пример <code>JsonBody</code> с валидацией и вложенными схемами</summary>

```Python hl_lines="9 14 15"
from rapidy.request_params import JsonBody

class UserAddress(BaseModel):
    city: str = Field(min_length=1, max_length=100)
    street: str = Field(min_length=1, max_length=100)

class UserData(BaseModel):
    age: int = Field(ge=18, lt=120)
    address: UserAddress

@routes.get('/')
async def handler(
        request: web.Request,
        username: Annotated[str, JsonBody(min_length=1, max_length=100)],
        userdata: Annotated[UserData, JsonBody(alias='userData')],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### JsonBodySchema
<details open>
<summary><code>JsonBodySchema</code></summary>

```Python hl_lines="5 10"
from pydantic import BaseModel
from rapidy.request_params import JsonBodySchema

class UserData(BaseModel):
    username: str

@routes.get('/')
async def handler(
        request: web.Request,
        user_data: Annotated[UserData, JsonBodySchema],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

<details>
<summary>Расширенный пример <code>JsonBodySchema</code> с валидацией и вложенными схемами</summary>

```Python hl_lines="19"
from pydantic import BaseModel, Field
from rapidy.request_params import JsonBodySchema

class UserAddress(BaseModel):
    city: str = Field(min_length=1, max_length=100)
    street: str = Field(min_length=1, max_length=100)

class UserData(BaseModel):
    age: int = Field(ge=18, lt=120)
    address: UserAddress

class BodyData(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    userdata: UserData = Field(alias='userData')

@routes.get('/')
async def handler(
        request: web.Request,
        body: Annotated[BodyData, JsonBodySchema],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### JsonBodyRaw
<details open>
<summary><code>JsonBodyRaw</code></summary>

```Python hl_lines="7"
from typing import Dict, Any
from rapidy.request_params import JsonBodyRaw

@routes.get('/')
async def handler(
        request: web.Request,
        body: Annotated[Dict[str, Any], JsonBodyRaw],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

!!! warning "Внимание"
    JsonBodyRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров.
