# Query parameters

## Типы данных

### Query
<details open>
<summary><code>Query</code></summary>

```Python hl_lines="6 7"
from rapidy.request_params import Query

@routes.get('/')
async def handler(
        request: web.Request,
        user_id: Annotated[int, Query(alias='UserId')],
        user_filter_value: Annotated[str, Query(alias='UserFilterValue')],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### QuerySchema
<details open>
<summary><code>QuerySchema</code></summary>

```Python hl_lines="5 6 11"
from pydantic import BaseModel, Field
from rapidy.request_params import QuerySchema

class QueryRequestSchema(BaseModel):
    user_id: int = Field(alias='UserId')
    user_filter_value: str = Field(alias='UserFilterValue')

@routes.get('/')
async def handler(
        request: web.Request,
        query_params: Annotated[QueryRequestSchema, QuerySchema],
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

### QueryRaw
<details open>
<summary><code>QueryRaw</code></summary>

```Python hl_lines="7"
from typing import Dict
from rapidy.request_params import QueryRaw

@routes.get('/')
async def handler(
        request: web.Request,
        query_params: Annotated[Dict[str, str], QueryRaw],  # {"some_key": <some_value>, ...}
) -> web.Response:
    return web.json_response({'data': 'success'})
```
</details>

!!! warning "Внимание"
    QueryRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см <a href="#raw">Особенности Raw параметров

## Ключевые особенности

### Использование именованных ресурсов
 стоит ли указать, что я про это уже рассказывал?