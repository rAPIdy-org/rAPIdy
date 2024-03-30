# Cookie parameters

## Ключевые особенности

## Типы данных

### Cookie
<details open>
<summary><code>Cookie</code></summary>

```Python hl_lines="6 7"
from rapidy.request_params import Cookie

@routes.get('/')
async def handler(
        request: web.Request,
        user_id: Annotated[int, Cookie(alias='UserId')],
        user_session: Annotated[str, Cookie(alias='UserSession')],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### CookieSchema
<details open>
<summary><code>CookieSchema</code></summary>

```Python hl_lines="5 6 11"
from pydantic import BaseModel, Field
from rapidy.request_params import CookieSchema

class CookiesRequestSchema(BaseModel):
    user_id: int = Field(alias='UserId')
    user_session: str = Field(alias='UserSession')

@routes.get('/')
async def handler(
        request: web.Request,
        cookies: Annotated[CookiesRequestSchema, CookieSchema],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### CookieRaw
<details open>
<summary><code>CookieRaw</code></summary>

```Python hl_lines="7"
from typing import Dict
from rapidy.request_params import CookieRaw

@routes.get('/')
async def handler(
        request: web.Request,
        cookies: Annotated[Dict[str, str], CookieRaw],  # {"some_key": <some_value>, ...}
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

!!! warning "Внимание"
    CookieRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров.</a>
