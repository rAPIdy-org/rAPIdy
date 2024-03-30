# FormData

## Ключевые особенности

duplicates parse as array - с примерами

## Типы данных

### FormDataBody
<details open>
<summary><code>FormDataBody</code></summary>

```Python hl_lines="6"
from rapidy.request_params import FormDataBody

@routes.get('/')
async def handler(
        request: web.Request,
        username: Annotated[str, FormDataBody],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

<details>
<summary>Расширенный пример <code>FormDataBody</code> с дополнительной валидацией</summary>

```Python hl_lines="6 7"
from rapidy.request_params import FormDataBody

@routes.get('/')
async def handler(
        request: web.Request,
        username: Annotated[str, FormDataBody(min_length=1, max_length=100)],
        age: Annotated[int, FormDataBody(ge=18, lt=120)],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### FormDataBodySchema
<details open>
<summary><code>FormDataBodySchema</code></summary>

```Python hl_lines="10"
from pydantic import BaseModel
from rapidy.request_params import FormDataBodySchema

class UserData(BaseModel):
    username: str

@routes.get('/')
async def handler(
        request: web.Request,
        user_data: Annotated[UserData, FormDataBodySchema],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

<details>
<summary>Расширенный пример <code>FormDataBodySchema</code> с дополнительной валидацией</summary>

```Python hl_lines="19"
from pydantic import BaseModel, Field
from rapidy.request_params import FormDataBodySchema

class UserData(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=18, lt=120)

@routes.get('/')
async def handler(
        request: web.Request,
        body: Annotated[UserData, FormDataBodySchema],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### FormDataBodyRaw
<details open>
<summary><code>FormDataBodyRaw</code></summary>

```Python hl_lines="7"
from typing import Dict, Any
from rapidy.request_params import FormDataBodyRaw

@routes.get('/')
async def handler(
        request: web.Request,
        body: Annotated[Dict[str, Any], FormDataBodyRaw],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

!!! warning "Внимание"
    FormDataBodyRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров.</a>
