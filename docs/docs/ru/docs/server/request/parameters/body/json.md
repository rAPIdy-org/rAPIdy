# Json

Json (JavaScript Object Notation) *(mime-type: `application/json`)* - текстовый формат обмена структурированными 
данными, основанный на JavaScript. Сейчас формат независим от JS и может использоваться в любом языке программирования. 

## Типы данных в JSON
В качестве значений в JSON могут быть использованы:

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

class UserData(BaseModel):
    username: str
    password: str

@routes.post('/')
async def handler(
    user_data: UserData = web.Body(),
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
    -d '111' \
    http://127.0.0.1:8080
    ```

### Литералы
true (логическое значение «истина»), false (логическое значение «ложь») и null
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
    -d 'SomeString' \
    http://127.0.0.1:8080
    ```

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
