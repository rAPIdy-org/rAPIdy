# Headers
Заголовки HTTP позволяют клиенту и серверу отправлять дополнительную информацию с HTTP запросом или ответом.

Данный раздел покажет, как можно извлекать и проверять заголовки используя **`Rapidy`**.

## Header
`Header` извлекает один конкретный заголовок.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

```Python
@routes.get('/')
async def handler(host: str = web.Header(alias='Host')) -> ...:
```

```Python
@routes.get('/')
async def handler(
    host: str = web.Header(alias='Host'),
    keep_alive: str = web.Header(alias='Keep-Alive'),
) -> ...:
```

## Headers
`Headers` извлекает сразу все заголовки.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

### Извлечение в готовую схему
#### pydantic.BaseModel
```Python
from pydantic import BaseModel, Field

class HeadersData(BaseModel):
    host: str = Field(alias='Host')
    keep_alive: str = Field(alias='Keep-Alive')

@routes.get('/')
async def handler(
    headers_data: HeadersData = web.Headers(),
) -> ...:
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве типа модели, но у вас не получится
    задать `alias` используя стандартные инструменты `dataclasses.dataclass`.

```Python
from dataclasses import dataclass

@dataclass
class HeadersData:
    host: str
    keep_alive: str  # cannot extract if header name is 'Keep-Alive'

@routes.get('/')
async def handler(
    headers_data: HeadersData = web.Headers(),
) -> ...:
# {"errors": [{"type": "missing", "loc": ["header", "keep_alive" ], "msg": "Field required"}]}
```

### Извлечение в словарь
```Python
@routes.get('/')
async def handler(
    headers_data: dict[str, str] = web.Headers(),
) -> ...:
# {Host': '0.0.0.0:8080', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'User-Agent': '...'}
```

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."

!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp` для этого http-параметра."
    - `Header` - `str`
    - `Headers` - `CIMultiDictProxy[str]`

Если по какой-то причине вам необходимо пропустить шаг с валидацией, воспользуйтесь следующими способами:

### Прямое отключение валидации
Установите параметру `Header` или `Headers` аттрибут `validate=False`

```python
header_host: int = web.Header(alias='Host', validate=False)
# "0.0.0.0:8080"

headers_data: int = web.Headers(validate=False)
# <CIMultiDictProxy('Host': '0.0.0.0:8080', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'User-Agent': '...')>
```

### Отключение с использованием `Any`
```python
header_host: Any = web.Header(alias='Host')
# "0.0.0.0:8080"

headers_data: Any = web.Headers()
# <CIMultiDictProxy('Host': '0.0.0.0:8080', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'User-Agent': '...')>
```

### Не используйте типипизацию
Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
```python
header_host=web.Header(alias='Host')
# "0.0.0.0:8080"

headers_data=web.Headers()
# <CIMultiDictProxy('Host': '0.0.0.0:8080', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1', 'User-Agent': '...')>
```

## Значения по умолчанию
Значение по умолчанию для `Header` будет использоваться, если в поступившем запросе не будет найден 
`заголовок` с таким именем.

Значение по умолчанию для `Headers` будет использоваться, если в поступившем запросе не будет найдено 
ни одного `заголовка`.

!!! note "Значение по умолчанию для `Headers` невозможный сценарий"
    Любой http-клиент все равно отправит базовые заголовки, поэтому значение по умолчанию для `Headers`
    никогда не будет выполнено. Но если вдруг это произойдет - это будет работать как нужно.

### default
```python
@routes.get('/')
async def handler(
    some_header: str = web.Header(alias='Some-Header', default='SomeValue'),
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_header: Annotated[str, web.Header(alias='Some-Header', default='SomeValue')],
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_header: Annotated[str, web.Header(alias='Some-Header')] = 'SomeValue',
) -> None:
```

### default_factory
```python
@routes.get('/')
async def handler(
    some_header: str = web.Header(alias='Some-Header', default_factory=lambda: 'SomeValue'),
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_header: Annotated[str, web.Header(alias='Some-Header', default_factory=lambda:'SomeValue')],
) -> None:
```

!!! warning "Нельзя использовать одновременно `dafault` и `default_factory`"
    Будет поднято исключение `pydantic` - `TypeError('cannot specify both default and default_factory')`

## Предупреждения и особенности
### Одновременное использование разных типов
!!! warning "В одном обработчике невозможно использовать одновременно `Header` и `Headers`"
```python
@routes.get('/')
async def handler(
    host: str = web.Header(alias='Host'),
    headers_data: HeadersData = web.Headers(),
) -> ...:
```

Во время запуска приложения будет вызвано исключение `AnotherDataExtractionTypeAlreadyExistsError`.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already use in handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `headers_data`
------------------------------
```

### Аттрибут `alias` для `Headers`
!!! note "Аттрибут `alias` во множественном параметре `web.Headers()` не будет работать."

```python
@routes.get('/')
async def handler(
    headers_data: HeadersData = web.Headers(alias='SomeName'),  # <-- alias not working
) -> ...:
```
