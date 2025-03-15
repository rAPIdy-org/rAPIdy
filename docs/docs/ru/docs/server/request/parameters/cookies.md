# Файлы cookie
В этом разделе рассматривается, как извлекать и проверять cookie с помощью **`Rapidy`**.

!!! note "Вы можете проверить данные, используя любой тип, поддерживаемый `pydantic`."

## Описание
**Cookie** — это небольшой набор данных о пользователе, который хранится на его устройстве без изменений и какой-либо обработки.

Веб-клиент при каждом обращении к соответствующему сайту передаёт эти данные веб-серверу в составе HTTP-запроса.

## Извлечение одиночного cookie
`Cookie` позволяет получить конкретный **cookie** по его имени.

```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/01_cookie.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/02_cookies.py !}
```

## Извлечение всех cookies
`Cookies` позволяет извлечь сразу все **cookies**.

### Извлечение в заранее заданную схему

#### pydantic.BaseModel
```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` поддерживаются в качестве модели, но задать `alias` стандартными средствами `dataclasses` невозможно.

```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/04_dataclass.py !}
```

### Извлечение в словарь
```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/05_dict.py !}
```

## Извлечение без валидации

!!! warning "Отключение валидации не рекомендуется."
    Если отключить валидацию, параметр вернёт базовую структуру `aiohttp`:

    - `Cookie` → `str`
    - `Cookies` → `Mapping[str, str]`

### Способы отключения валидации

#### Явное отключение
```python
{!> ./docs/docs/server/request/parameters/cookies/02_ignore_validation/01_validate_attr_false.py !}
```

#### Использование `Any`
```python
{!> ./docs/docs/server/request/parameters/cookies/02_ignore_validation/02_any_type.py !}
```

#### Отсутствие аннотации типа
Если тип не указан, по умолчанию будет установлен `Any`.
```python
{!> ./docs/docs/server/request/parameters/cookies/02_ignore_validation/03_no_type.py !}
```

## Значения по умолчанию
Значение по умолчанию для `Cookie` будет использоваться, если в поступившем запросе не будет найден
`cookie` с таким именем.

Значение по умолчанию для `Cookies` будет использоваться, если в поступившем запросе не будет найдено
ни одного `cookie`.

### Использование `default`
```python
{!> ./docs/docs/server/request/parameters/cookies/03_default/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/03_default/02_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/03_default/03_example.py !}
```

### Использование `default_factory`
```python
{!> ./docs/docs/server/request/parameters/cookies/04_default_factory/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/04_default_factory/02_example.py !}
```

!!! warning "Нельзя одновременно использовать `default` и `default_factory`."
    При попытке указать оба параметра будет вызвано исключение `pydantic`:
    ```python
    TypeError('cannot specify both default and default_factory')
    ```

## Предупреждения и особенности

### Одновременное использование `Cookie` и `Cookies`
!!! warning "Невозможно использовать `Cookie` и `Cookies` одновременно в одном обработчике."

```python
{!> ./docs/docs/server/request/parameters/cookies/05_diff_types.py !}
```

При запуске приложения будет вызвано исключение `AnotherDataExtractionTypeAlreadyExistsError`.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already use in handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `cookie_data`
------------------------------
```

### Атрибут `alias` в `Cookies`

!!! note "Атрибут `alias` не работает в параметре `Cookies()`."
```python
{!> ./docs/docs/server/request/parameters/cookies/06_alias.py !}
```

## Как извлекаются сырые данные

Внутри `Rapidy` используется метод `cookies` объекта `Request`, после чего полученные данные передаются в `pydantic` для валидации.

!!! info "Как происходит извлечение внутри `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/cookies/07_extract_raw.py !}
    ```

!!! note "`Rapidy` использует встроенные механизмы `aiohttp`"
    Подробнее об объекте `aiohttp.Request` и методах извлечения данных можно узнать
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.
