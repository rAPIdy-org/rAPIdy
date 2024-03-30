# Header parameters

## Типы данных
### Header
!!! example "Header"
    ```Python hl_lines="10 11"
    {!> ./parameters/header/types/Header/ex_01.py !}
    ```
    !!! tip ""
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.

        # TODO!!!! доделать -> curl или постман

        После старта сервера, если вы перейдёте по адресу: 
        <a href="http://127.0.0.1:8080/user_1/param_2" target="blank">http://127.0.0.1:8080/user_1/param_2</a>
        , то увидите ответ: `{"user_id": "user_1", "some_param", "param_2"}`.

### HeaderSchema
!!! example "HeaderSchema"
    ```Python hl_lines="9 10 15"
    {!> ./parameters/header/types/Header/ex_02.py !}
    ```

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


