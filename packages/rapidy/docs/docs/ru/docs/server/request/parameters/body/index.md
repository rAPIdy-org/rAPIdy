# Тело HTTP-запроса
Этот раздел покажет, как извлекать и проверять `body` с помощью **`Rapidy`**.

## Описание
**HTTP тело запроса** — это часть запроса, передающая данные от клиента к серверу. Оно играет ключевую роль в методах `POST`, `PUT` и `PATCH`, которые
используются для создания, обновления и модификации ресурсов.

Например, при `POST`-запросе для создания учетной записи пользователя данные передаются в теле запроса.

```python
{!> ./docs/docs/server/request/parameters/body/index/01_index.py !}
```

---

## Атрибуты Body

### `content_type`
```python
# `application/json` by default
content_type: str | ContentType = ContentType.json
```
Определяет ожидаемый сервером тип данных в `body`.

!!! tip "Подробнее про `enum ContentType` можно прочитать **[здесь](../../../../enums/index.md)**."

`Rapidy` использует заданный `content_type` для корректного извлечения данных.

!!! info "Основные поддерживаемые типы:"
    - `application/json`
    - `application/x-www-form-urlencoded`
    - `multipart/form-data`
    - `text/*` — любые MIME-типы с текстовыми данными
    - `application/octet-stream`

    !!! warning ""
        Если сервер ожидает формат, который `Rapidy` явно не поддерживает (например, `video/mpeg`), данные будут извлечены как `bytes` и переданы в `pydantic`-модель без обработки.

---

### `check_content_type`
Определяет, нужно ли проверять заголовок `Content-Type`.

- При `True` *(значение по умолчанию)* `Rapidy` сравнит переданный заголовок `Content-Type` с ожидаемым `content_type`.
  Если они не совпадают, клиенту вернется ошибка:

```json
{
    "errors": [
        {
            "type": "ExtractError",
            "loc": [
                "body"
            ],
            "msg": "Failed to extract body data: Expected Content-Type `text/plain`, got `<current_request_content_type>`"
        }
    ]
}
```

---

### `json_decoder`
Позволяет задать пользовательский `json_decoder` для обработки JSON-данных в теле запроса.

!!! note "Работает только при `content_type="application/json"`."

По умолчанию `Rapidy` использует `json.loads` без параметров.

!!! example "Эквивалентные примеры:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/01_default_decoder.py !}
    ```
    или
    ```python
    {!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/02_default_decoder.py !}
    ```

Если требуется кастомная обработка JSON, передайте в `json_decoder` любой вызываемый объект, принимающий `str`.

!!! note "Ожидаемый тип данных: `Callable[[str], Any]`."

!!! example "Пример с пользовательским декодером:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/03_custom_decoder.py !}
    ```

Чтобы использовать `json.loads` с параметрами или передать декодер с аргументами, воспользуйтесь `functools.partial`:

```python
{!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/04_decoder_with_params.py !}
```

---

## Извлечение без валидации
Большинство типов `Body` поддерживают извлечение данных без валидации.

!!! warning "Этот метод не рекомендуется."
!!! note "Если валидация отключена, параметр вернет базовую структуру `aiohttp`."
!!! note "Подробнее об этом можно прочитать в разделе **Извлечение без валидации** для каждого типа `body`."

### Способы отключения валидации:

#### Явное отключение
```python
{!> ./docs/docs/server/request/parameters/body/index/03_ignore_validation/01_validate_attr_false.py !}
```

#### Использование `Any`
```python
{!> ./docs/docs/server/request/parameters/body/index/03_ignore_validation/02_any_type.py !}
```

#### Отсутствие аннотации типа
Если тип не указан, по умолчанию используется `Any`.
```python
{!> ./docs/docs/server/request/parameters/body/index/03_ignore_validation/03_no_type.py !}
```

---

## Значения по умолчанию
Большинство типов `Body` поддерживают значения по умолчанию.

Если HTTP-запрос не содержит тела, параметр получит указанное значение по умолчанию (если оно задано).

### Примеры использования

#### Указано значение по умолчанию
```python
{!> ./docs/docs/server/request/parameters/body/index/04_default/01_default_exists.py !}
```

#### Опциональное тело запроса
```python
{!> ./docs/docs/server/request/parameters/body/index/04_default/02_default_optional.py !}
```

!!! note "Подробнее об этом можно прочитать в разделе **Значения по умолчанию** для каждого типа `body`."
