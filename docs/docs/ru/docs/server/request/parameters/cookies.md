# Cookies

Cookie – небольшой набор данных о пользователе хранимый на его устройстве без изменений и какой-либо обработки.

Веб-клиент всякий раз при обращении к соответствующему сайту пересылает эти данные веб-серверу 
в составе HTTP-запроса.

Данный раздел покажет, как можно извлекать и проверять cookie используя **`Rapidy`**.

## Cookie
`Cookie` извлекает одиночный **cookie** по его имени.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

```Python
@routes.get('/')
async def handler(user_id: str = web.Cookie(alias='UserID')) -> ...:
```

```Python
@routes.get('/')
async def handler(
    user_id: str = web.Cookie(alias='UserID'),
    user_session: str = web.Cookie(alias='UserSession'),
) -> ...:
```

## Cookies
`Cookies` извлекает сразу все **cookies**.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

### Извлечение заголовков в готовую схему
#### pydantic.BaseModel
```Python
from pydantic import BaseModel, Field

class CookieData(BaseModel):
    user_id: str = Field(alias='UserID')
    user_session: str = Field(alias='User-Session')

@routes.get('/')
async def handler(
    cookie_data: CookieData = web.Cookies(),
) -> ...:
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве типа модели, но у вас не получится
    задать `alias` используя стандартные инструменты `dataclasses.dataclass`, чтобы извлечь cookie.

```Python
from dataclasses import dataclass

@dataclass
class CookieData:
    UserID: str  # camelCase syntax :c
    user_session: str  # cannot extract if cookie name is 'User-Session'

@routes.get('/')
async def handler(
    cookie_data: CookieData = web.Cookies(),
) -> ...:
# {"errors": [{"type": "missing", "loc": ["cookie", "user_session"], "msg": "Field required"}]}
```

### Извлечение в словарь
```Python
@routes.get('/')
async def handler(
    cookie_data: dict[str, str] = web.Cookies(),
) -> ...:
# {'UserID': ..., 'User-Session': ...}
```

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."

!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp` для этого http-параметра."
    - `Cookie` - `str`
    - `Cookies` - `Mapping[str, str]`


Если по какой-то причине вам необходимо пропустить шаг с валидацией, воспользуйтесь следующими способами:

### Прямое отключение валидации
Установите параметру `Cookie` или `Cookies` аттрибут `validate=False`

```python
user_id: int = web.Cookie(alias='UserID', validate=False)
# ...

cookie_data: int = web.Cookies(validate=False)
# {'UserID': ..., 'User-Session': ...}
```

### Отключение с использованием `Any`
```python
user_id: Any = web.Cookie(alias='UserID')
# ...

headers_data: Any = web.Cookies()
# {'UserID': ..., 'User-Session': ...}
```

### Не используйте типипизацию
Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
```python
user_id=web.Cookie(alias='UserID')
# ...

headers_data=web.Cookies()
# {'UserID': ..., 'User-Session': ...}
```

## Значения по умолчанию
### default
```python
@routes.get('/')
async def handler(
    some_cookie: str = web.Cookie(alias='Some-Cookie', default='SomeValue'),
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_cookie: Annotated[str, web.Cookie(alias='Some-Cookie', default='SomeValue')],
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_cookie: Annotated[str, web.Cookie(alias='Some-Cookie')] = 'SomeValue',
) -> None:
```

### default_factory
```python
@routes.get('/')
async def handler(
    some_cookie: str = web.Cookie(alias='Some-Cookie', default_factory=lambda: 'SomeValue'),
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_cookie: Annotated[str, web.Cookie(alias='Some-Cookie', default_factory=lambda:'SomeValue')],
) -> None:
```

!!! warning "Нельзя использовать одновременно `dafault` и `default_factory`"
    Будет поднято исключение `pydantic` - `TypeError('cannot specify both default and default_factory')`

## Предупреждения и особенности
### Одновременное использование разных типов
!!! warning "В одном обработчике невозможно использовать одновременно `Cookie` и `Cookies`"
```python
@routes.get('/')
async def handler(
    user_id: str = web.Cookie(alias='UserID'),
    cookie_data: CookieData = web.Cookies(),
) -> ...:
```

Во время запуска приложения будет вызвано исключение `AnotherDataExtractionTypeAlreadyExistsError`.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already use in handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `cookie_data`
------------------------------
```

### Аттрибут `alias` для `Cookies`
!!! note "Аттрибут `alias` во множественном параметре `web.Cookies()` не будет работать."

```python
@routes.get('/')
async def handler(
    headers_data: CookieData = web.Cookies(alias='SomeName'),  # <-- alias not working
) -> ...:
```
