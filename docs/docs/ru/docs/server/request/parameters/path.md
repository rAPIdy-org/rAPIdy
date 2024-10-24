# Path
## Описание
**Path-параметры** позволяют строить **динамические маршруты** внутри вашего приложения.

Вы можете определить path-параметры используя синтаксис форматированных строк Python:
```Python hl_lines="1"
@routes.get('/{user_id}')
async def handler(
    user_id: str = web.PathParam(),
) -> ...:
```

!!! note "Подробнее про динамические маршруты в `aiohttp` можно прочитать **<a href="https://docs.aiohttp.org/en/stable/web_quickstart.html#aiohttp-web-variable-handler" target="_blank">здесь</a>**."

Данный раздел покажет, как можно извлекать и проверять path-параметры используя **`Rapidy`**.

!!! tip "Более детальные сценарии применения вы найдете в примерах - **[Examples](../../../../examples.md)**."

## PathParam
`PathParam` извлекает одиночный **path-параметр**.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

```Python
@routes.get('/{user_id}')
async def handler(
    user_id: str = web.PathParam(),
) -> ...:
```

```Python
@routes.get('/{user_id}/{user_data}')
async def handler(
    user_id: str = web.PathParam(),
    user_data: str = web.PathParam(),
) -> ...:
```

## PathParams
`PathParams` извлекает сразу все **path-параметры**.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

### Извлечение в готовую схему
#### pydantic.BaseModel
```Python
from pydantic import BaseModel

class PathData(BaseModel):
    user_id: str
    user_data: str

@routes.get('/{user_id}/{user_data}')
async def handler(
    path_data: PathData = web.PathParams(),
) -> ...:
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве типа модели, но у вас не получится
    задать `alias` используя стандартные инструменты `dataclasses.dataclass`.

```Python
from dataclasses import dataclass

@dataclass
class PathData:
    user_id: str
    user_data: str

@routes.get('/{user_id}/{user_data}')
async def handler(
    path_data: PathData = web.PathParams(),
) -> ...:
```

### Извлечение в словарь
```Python
@routes.get('/{user_id}/{user_data}')
async def handler(
    path_data: dict[str, str] = web.PathParams(),
) -> ...:
# {'user_id': ..., 'user_data': ...}
```

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."

!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp` для этого http-параметра."
    - `PathParam` - `str`
    - `PathParams` - `dict[str, str]`

Если по какой-то причине вам необходимо пропустить шаг с валидацией, воспользуйтесь следующими способами:

!!! info "Прямое отключение валидации"
    Установите параметру `PathParam` или `PathParams` аттрибут `validate=False`

    ```python
    user_id: int = web.PathParam(validate=False)
    # ...
    
    path_data: int = web.PathParams(validate=False)
    # {'user_id': ..., 'user_data': ...}
    ```

!!! info "Отключение с использованием `Any`"
    ```python
    user_id: Any = web.PathParam()
    # ...
    
    path_data: Any = web.PathParams()
    # {'user_id': ..., 'user_data': ...}
    ```

!!! info "Не используйте типипизацию"
    Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
    ```python
    user_id=web.PathParam()
    # ...
    
    path_data=web.PathParams()
    # {'user_id': ..., 'user_data': ...}
    ```

## Значения по умолчанию
!!! warning "`PathParam` и `PathParams` не поддерживают значения по умолчанию."
    Это вполне логичное архитектурное ограничение. Без этого решения невозможно правильно построить
    динамическую работу роутеров.

### default
```python
@routes.get('/{user_id}')
async def handler(
    user_id: str = web.PathParam(default='test_user_id'),
) -> None:
```
```python
@routes.get('/{user_id}')
async def handler(
    user_id: Annotated[str, web.PathParam(default='test_user_id')],
) -> None:
```
```python
@routes.get('/{user_id}')
async def handler(
    user_id: Annotated[str, web.PathParam()] = 'test_user_id',
) -> None:
```
Во время запуска приложения будет вызвано исключение `ParameterCannotUseDefaultError`.

```
------------------------------
Handler attribute with Type `PathParam` cannot have a default value.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `user_id`
------------------------------
```

### default_factory
```python
@routes.get('/{user_id}')
async def handler(
    user_id: str = web.PathParam(default_factory=lambda: 'test_user_id'),
) -> None:
```
```python
@routes.get('/{user_id}')
async def handler(
    user_id: Annotated[str, web.PathParam(default_factory=lambda: 'test_user_id')],
) -> None:
```

Во время запуска приложения будет вызвано исключение  `ParameterCannotUseDefaultFactoryError`

```
------------------------------
Handler attribute with Type `PathParam` cannot have a default_factory.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `user_id`
------------------------------
```

## Предупреждения и особенности
### Одновременное использование разных типов
!!! warning "В одном обработчике невозможно использовать одновременно `PathParam` и `PathParams`"
```python
@routes.get('/{user_id}/{user_data}')
async def handler(
        user_id: str = web.PathParam(),
        path_data: PathData = web.PathParams(),
) -> ...:
```

Во время запуска приложения будет вызвано исключение `AnotherDataExtractionTypeAlreadyExistsError`.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already use in handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `path_data`
------------------------------
```

### Аттрибут `alias` для `PathParams`
!!! note "Аттрибут `alias` во множественном параметре `web.PathParams()` не будет работать."

```python
@routes.get('/{user_id}/{user_data}')
async def handler(
    path_data: PathData = web.PathParams(alias='SomeName'),  # <-- alias not working
) -> ...:
```

## Как извлекаются сырые данные
`Rapidy` внутри себя использует вызов `match_info` объекта `Request`, а затем передает полученный объект на валидацию 
в `pydantic` модель.

!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_path(request: Request) -> dict[str, str]:
        return dict(request.match_info)
    ```

!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.
