# Header parameters

## Типы данных
### Header
<details open>
<summary><code>Header</code></summary>

```Python hl_lines="6 7"
from rapidy.request_params import Header

@routes.get('/')
async def handler(
        request: web.Request,
        host: Annotated[str, Header(alias='Host')],
        auth_token: Annotated[str, Header(alias='Authorization')],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### HeaderSchema
<details open>
<summary><code>HeaderSchema</code></summary>

```Python hl_lines="5 6 11"
from pydantic import BaseModel, Field
from rapidy.request_params import HeaderSchema

class HeadersRequestSchema(BaseModel):
    host: int = Field(alias='Host')
    auth_token: str = Field(alias='Authorization')

@routes.get('/')
async def handler(
        request: web.Request,
        headers: Annotated[HeadersRequestSchema, HeaderSchema],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### HeaderRaw
<details open>
<summary><code>HeaderRaw</code></summary>

```Python hl_lines="7"
from typing import Dict
from rapidy.request_params import HeaderRaw

@routes.get('/')
async def handler(
        request: web.Request,
        headers: Annotated[Dict[str, str], HeaderRaw],  # {"Host": "127.0.0.1", ...}
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

!!! warning "Внимание"
    HeaderRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров.</a>

## Ключевые особенности


