# Параметры пути
В этом разделе описаны способы извлечения и валидации path-параметров в **`Rapidy`**.

!!! note "Вы можете проверять данные, используя любой тип, поддерживаемый `pydantic`."

## Описание
**Path-параметры** позволяют создавать **динамические маршруты** в вашем приложении.

Вы можете определить path-параметры, используя синтаксис форматированных строк Python:

```Python hl_lines="1"
{!> ./docs/docs/server/request/parameters/path/01_index.py !}
```

!!! note "Подробнее о динамических маршрутах в `aiohttp` можно прочитать **<a href="https://docs.aiohttp.org/en/stable/web_quickstart.html#aiohttp-web-variable-handler" target="_blank">здесь</a>**."

## Извлечение одиночного параметра пути
`PathParam` позволяет извлечь одиночный **path-параметр**.

```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/01_path.py !}
```

```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/02_paths.py !}
```

## Извлечение всех параметров пути
`PathParams` позволяет извлечь сразу все **path-параметры**.

### Извлечение в заранее заданную схему

#### pydantic.BaseModel
```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве модели, но задать `alias` стандартными средствами `dataclasses` невозможно.

```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/04_dataclass.py !}
```

### Извлечение в словарь
```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/05_dict.py !}
```

## Извлечение без валидации

!!! warning "Отключение валидации не рекомендуется."
    Если валидация отключена, параметры возвращаются в базовой структуре `aiohttp`:

    - `PathParam` → `str`
    - `PathParams` → `dict[str, str]`

### Способы отключения валидации

#### Явное отключение
```python
{!> ./docs/docs/server/request/parameters/path/03_ignore_validation/01_validate_attr_false.py !}
```

#### Использование `Any`
```python
{!> ./docs/docs/server/request/parameters/path/03_ignore_validation/02_any_type.py !}
```

#### Отсутствие аннотации типа
Если тип не указан, по умолчанию используется `Any`.
```python
{!> ./docs/docs/server/request/parameters/path/03_ignore_validation/03_no_type.py !}
```

## Значения по умолчанию
!!! warning "`PathParam` и `PathParams` не поддерживают значения по умолчанию."
    Это осознанное архитектурное ограничение: без него невозможно корректно реализовать
    динамическую маршрутизацию.

!!! warning ""
    Попытка установить `default` или `default_factory` для path-параметра
    приведёт к исключению `ParameterCannotUseDefaultError` или `ParameterCannotUseDefaultFactoryError`.

## Предупреждения и особенности

### Одновременное использование `PathParam` и `PathParams`

!!! warning "Нельзя использовать `PathParam` и `PathParams` одновременно в одном обработчике."

```python
{!> ./docs/docs/server/request/parameters/path/04_diff_types.py !}
```

При запуске приложения будет вызвано исключение `AnotherDataExtractionTypeAlreadyExistsError`:

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already used in the handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `path_data`
------------------------------
```

### Атрибут `alias` для `PathParams`

!!! note "Атрибут `alias` не работает в параметре `PathParams()`."

```python
{!> ./docs/docs/server/request/parameters/path/05_alias.py !}
```

## Извлечение сырых данных

В `Rapidy` используется метод `match_info` объекта `Request`, после чего полученные данные передаются в `pydantic` для валидации.

!!! info "Как происходит извлечение внутри `Rapidy`"

    ```python
    {!> ./docs/docs/server/request/parameters/path/06_extract_raw.py !}
    ```

!!! note "`Rapidy` использует встроенные механизмы `aiohttp`."
    Подробнее об объекте `aiohttp.Request` и методах извлечения данных можно узнать
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.
