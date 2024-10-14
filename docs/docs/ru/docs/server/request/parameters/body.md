# Body

HTTP тело запроса является частью сообщения запроса, переносящего данные от клиента к серверу. 
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

!!! tip "Более детальные сценарии применения вы найдете в примерах - **[Examples](../../../../examples.md)**."

## Json

Json (JavaScript Object Notation) *(mime-type: `application/json`)* - текстовый формат обмена структурированными 
данными, основанный на JavaScript.

При этом формат независим от JS и может использоваться в любом языке программирования. 

В качестве значений в JSON могут быть использованы:

### JSON-объект
Неупорядоченное множество пар «ключ:значение».
```
{
    "username: "User",
    "password": "myAwesomePass"
}
```
Код `Rapidy`:
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
Отправка с помощью `curl`
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
Код `Rapidy`:
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
Отправка с помощью `curl`
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
Отправка с помощью `curl`
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
Код `Rapidy`:
```python
@routes.post('/')
async def handler(
    bool_data: bool = web.Body(),
) -> ...:
```
Отправка с помощью `curl`
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
Код `Rapidy`:
```python
@routes.post('/')
async def handler(
    string_data: str = web.Body(),
) -> ...:
```
Отправка с помощью `curl`
```bash
curl -X POST \
-H "Content-Type: application/json" \
-d 'SomeString' \
http://127.0.0.1:8080
```





## X-WWW-Form-Urlencoded
application/x-www-form-urlencoded - является распространенным типом контента, используемым при отправке данных 
через HTML-формы в Интернете.

Это способ кодирования пар ключ-значение в виде строки в формате key1=value1&key2=value2.


## Multipart Form Data

## Text

## Binary

### Bytes
### StreamReader