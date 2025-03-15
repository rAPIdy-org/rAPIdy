# Параметры запроса
Данный раздел покажет, как можно извлекать и проверять query-params используя **`Rapidy`**.

!!! note "Вы можете проверить данные, используя любой тип, поддерживаемый `pydantic`."

## Описание
**Query-параметры** представляют собой набор пар ключ-значение, которые идут после знака <span class="green-color">?</span> в URL-адресе,
разделенные символами <span class="green-color">&</span>.

!!! example "Пример URL со строкой запроса, включающей три параметра."
    https://www.rapidy.com/search<span class="green-color">?</span><span class="base-color">query</span>=<span class="note-color">database+tools</span><span class="green-color">&</span><span class="base-color">star_rating</span>=<span class="note-color">4</span><span class="green-color">&</span><span class="base-color">order</span>=<span class="note-color">alphabetical</span>

## QueryParam
`QueryParam` извлекает одиночный **query-параметр** по его имени.

```python
{!> ./docs/docs/server/request/parameters/query/01_extract/01_query_param.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/01_extract/02_query_params.py !}
```

## QueryParams
`QueryParams` извлекает сразу все **query-параметры**.

!!! note "Помните, вы можете проверить данные используя любой тип поддерживаемый `pydantic`."

### Извлечение в готовую схему
#### pydantic.BaseModel
```Python
{!> ./docs/docs/server/request/parameters/query/01_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве типа модели, но у вас не получится
    задать `alias` используя стандартные инструменты `dataclasses.dataclass`.

```Python
{!> ./docs/docs/server/request/parameters/query/01_extract/04_dataclass.py !}
```

### Извлечение в словарь
```Python
{!> ./docs/docs/server/request/parameters/query/01_extract/05_dict.py !}
```

## Извлечение без валидации

!!! warning "Отключение валидации не рекомендуется."
    Если отключить валидацию, параметр вернёт базовую структуру `aiohttp`:

    - `QueryParam` - `str`
    - `QueryParams` - `MultiDictProxy[str]`

### Способы отключения валидации

#### Явное отключение
```python
{!> ./docs/docs/server/request/parameters/query/02_ignore_validation/01_validate_attr_false.py !}
```

#### Использование `Any`
```python
{!> ./docs/docs/server/request/parameters/query/02_ignore_validation/02_any_type.py !}
```

#### Отсутствие аннотации типа
Если тип не указан, по умолчанию используется `Any`.
```python
{!> ./docs/docs/server/request/parameters/query/02_ignore_validation/03_no_type.py !}
```

## Значения по умолчанию
Значение по умолчанию для `QueryParam` будет использоваться, если в поступившем запросе не будет найден `query-параметр` с таким именем.

Значение по умолчанию для `QueryParams` будет использоваться, если в поступившем запросе не будет найдено ни одного `query-параметра`.

### Использование `default`
```python
{!> ./docs/docs/server/request/parameters/query/03_default/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/03_default/02_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/03_default/03_example.py !}
```

### Использование `default_factory`
```python
{!> ./docs/docs/server/request/parameters/query/04_default_factory/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/04_default_factory/02_example.py !}
```

!!! warning "Нельзя одновременно использовать `default` и `default_factory`."
    При попытке задать оба параметра будет вызвано исключение `pydantic`:
    ```python
    TypeError('cannot specify both default and default_factory')
    ```

## Предупреждения и особенности

### Использование `QueryParam` и `QueryParams` одновременно
!!! warning "Невозможно использовать `QueryParam` и `QueryParams` одновременно в одном обработчике."
```python
{!> ./docs/docs/server/request/parameters/query/05_diff_types.py !}
```

При запуске приложения будет вызвано исключение `AnotherDataExtractionTypeAlreadyExistsError`.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already use in handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `headers_data`
------------------------------
```

### Атрибут `alias` в `QueryParams`

!!! note "Атрибут `alias` не работает в параметре `QueryParams()`."
```python
{!> ./docs/docs/server/request/parameters/query/06_alias.py !}
```

## Как извлекаются сырые данные
`Rapidy` используется метод `rel_url.query` объекта `Request`, после чего полученные данные передаются в `pydantic` для валидации.

!!! info "Как происходит извлечение внутри `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/query/07_extract_raw.py !}
    ```

!!! note "`Rapidy` использует встроенные механизмы `aiohttp`."
    Подробнее об объекте `aiohttp.Request` и методах извлечения данных можно узнать
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.
