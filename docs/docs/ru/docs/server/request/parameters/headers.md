# HTTP-заголовки
В этом разделе рассмотрим, как извлекать и проверять заголовки с помощью **`Rapidy`**.

!!! note "Вы можете проверить данные, используя любой тип, поддерживаемый `pydantic`."

## Описание
**HTTP-заголовки** позволяют клиенту и серверу обмениваться дополнительной информацией в HTTP-запросах и ответах.

## Извлечение одного заголовка
`Header` позволяет получить конкретный заголовок.



```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/01_header.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/02_headers.py !}
```

## Извлечение всех заголовков
`Headers` позволяет извлечь сразу все заголовки.

### Извлечение в заранее заданную схему

#### pydantic.BaseModel
```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве модели, но задать `alias` стандартными средствами `dataclasses` невозможно.

```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/04_dataclass.py !}
```

### Извлечение в словарь
```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/05_dict.py !}
```

## Извлечение без валидации

!!! warning "Отключение валидации не рекомендуется."
    Если отключить валидацию, параметр вернёт базовую структуру `aiohttp`:

    - `Header` → `str`
    - `Headers` → `CIMultiDictProxy[str]`

### Способы отключения валидации

#### Явное отключение
```python
{!> ./docs/docs/server/request/parameters/headers/02_ignore_validation/01_validate_attr_false.py !}
```

#### Использование `Any`
```python
{!> ./docs/docs/server/request/parameters/headers/02_ignore_validation/02_any_type.py !}
```

#### Отсутствие аннотации типа
Если тип не указан, по умолчанию используется `Any`.
```python
{!> ./docs/docs/server/request/parameters/headers/02_ignore_validation/03_no_type.py !}
```

## Значения по умолчанию
Значение по умолчанию для `Header` будет использовано, если в запросе отсутствует заголовок с указанным именем.

Значение по умолчанию для `Headers` будет использовано, если в запросе нет ни одного заголовка.

!!! note "Значение по умолчанию для `Headers` в реальности не применяется."
    Любой HTTP-клиент всегда отправляет базовые заголовки, поэтому этот случай практически невозможен.
    Однако, если такое вдруг произойдёт, механизм отработает корректно.

### Использование `default`
```python
{!> ./docs/docs/server/request/parameters/headers/03_default/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/03_default/02_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/03_default/03_example.py !}
```

### Использование `default_factory`
```python
{!> ./docs/docs/server/request/parameters/headers/04_default_factory/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/04_default_factory/02_example.py !}
```

!!! warning "Нельзя одновременно использовать `default` и `default_factory`."
    При попытке задать оба параметра будет вызвано исключение `pydantic`:
    ```python
    TypeError('cannot specify both default and default_factory')
    ```

## Предупреждения и особенности

### Использование `Header` и `Headers` одновременно
!!! warning "Невозможно использовать `Header` и `Headers` одновременно в одном обработчике."
```python
{!> ./docs/docs/server/request/parameters/headers/05_diff_types.py !}
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

### Атрибут `alias` в `Headers`

!!! note "Атрибут `alias` не работает в параметре `Headers()`."
```python
{!> ./docs/docs/server/request/parameters/headers/06_alias.py !}
```

## Как извлекаются сырые данные
В `Rapidy` используется метод `headers` объекта `Request`, после чего полученные данные передаются в `pydantic` для валидации.

!!! info "Как происходит извлечение внутри `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/headers/07_extract_raw.py !}
    ```

!!! note "`Rapidy` использует встроенные механизмы `aiohttp`."
    Подробнее об объекте `aiohttp.Request` и методах извлечения данных можно узнать
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.
