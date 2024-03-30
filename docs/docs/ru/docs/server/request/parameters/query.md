# QueryParams


Query-параметры представляют собой набор пар ключ-значение, которые идут после знака <span class="green-color">?</span> в URL-адресе, 
разделенные символами <span class="green-color">&</span>.

!!! example "Пример URL со строкой запроса, включающей три параметра."
    https://www.rapidy.com/search<span class="green-color">?</span><span class="base-color">query</span>=<span class="note-color">database+tools</span><span class="green-color">&</span><span class="base-color">star_rating</span>=<span class="note-color">4</span><span class="green-color">&</span><span class="base-color">order</span>=<span class="note-color">alphabetical</span>

Данный раздел покажет, как можно извлекать и проверять query-params используя **`Rapidy`**.

!!! tip "Более детальные сценарии применения вы найдете в примерах - **[Examples](../../../../examples.md)**."

## QueryParam
`QueryParam` извлекает одиночный **query-параметр** по его имени.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

```Python
@routes.get('/')
async def handler(
    query: str = web.QueryParam(),
) -> ...:
```

```Python
@routes.get('/')
async def handler(
    query: str = web.QueryParam(),
    star_rating: str = web.QueryParam(),
) -> ...:
```

## QueryParams
`QueryParams` извлекает сразу все **query-параметры**.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

### Извлечение в готовую схему
#### pydantic.BaseModel
```Python
from pydantic import BaseModel

class QueryParamsData(BaseModel):
    query: str
    star_rating: str

@routes.get('/')
async def handler(
    query_params_data: QueryParamsData = web.QueryParams(),
) -> ...:
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве типа модели, но у вас не получится
    задать `alias` используя стандартные инструменты `dataclasses.dataclass`.

```Python
from dataclasses import dataclass

@dataclass
class QueryParamsData:
    query: str
    star_rating: str

@routes.get('/')
async def handler(
    query_params_data: QueryParamsData = web.QueryParams(),
) -> ...:
```

### Извлечение в словарь
```Python
@routes.get('/')
async def handler(
    query_params_data: dict[str, str] = web.QueryParams(),
) -> ...:
# {'query': ..., 'star_rating': ...}
```

## Извлечение без валидации
!!! note "Эти способы не являются рекомендованными."

!!! note "Если валидация отключена, параметр выведет базовую структуру `aiohttp` для этого http-параметра."
    - `QueryParam` - `str`
    - `QueryParams` - `MultiDictProxy[str]`

Если по какой-то причине вам необходимо пропустить шаг с валидацией, воспользуйтесь следующими способами:

```python
query: int = web.QueryParam(validate=False)
# ...

query_params_data: int = web.QueryParams(validate=False)
# <MultiDictProxy('query': ..., 'star_rating', ...)>
```

### Отключение с использованием `Any`
```python
query: Any = web.QueryParam()
# ...

query_params_data: Any = web.QueryParams()
# <MultiDictProxy('query': ..., 'star_rating', ...)>
```

### Не используйте типипизацию
Если не указать тип вообще - по умолчанию внутри будет проставлен тип `Any`.
```python
query=web.QueryParam()
# ...

query_params_data=web.QueryParams()
# <MultiDictProxy('query': ..., 'star_rating', ...)>
```

## Значения по умолчанию
Значение по умолчанию для `QueryParam` будет использоваться, если в поступившем запросе не будет найден 
`query-параметр` с таким именем.

Значение по умолчанию для `QueryParams` будет использоваться, если в поступившем запросе не будет найдено 
ни одного `query-параметра`.

### default
```python
@routes.get('/')
async def handler(
    some_query_param: str = web.QueryParam(default='SomeValue'),
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_query_param: Annotated[str, web.QueryParam(default='SomeValue')],
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_query_param: Annotated[str, web.QueryParam()] = 'SomeValue',
) -> None:
```

### default_factory
```python
@routes.get('/')
async def handler(
    some_query_param: str = web.QueryParam(default_factory=lambda: 'SomeValue'),
) -> None:
```
```python
@routes.get('/')
async def handler(
    some_query_param: Annotated[str, web.QueryParam(default_factory=lambda:'SomeValue')],
) -> None:
```

!!! warning "Нельзя использовать одновременно `dafault` и `default_factory`"
    Будет поднято исключение `pydantic` - `TypeError('cannot specify both default and default_factory')`

## Как извлекаются сырые данные
`Rapidy` внутри себя использует вызов `rel_url.query` объекта `Request`, а затем передает полученный объект на валидацию 
в `pydantic` модель.

!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_query(request: Request) -> MultiDictProxy[str]:
        return request.rel_url.query
    ```

!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.
