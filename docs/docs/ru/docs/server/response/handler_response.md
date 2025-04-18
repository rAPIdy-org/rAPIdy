# Обработка HTTP-ответов
Раздел объясняет, как в **`Rapidy`** управлять HTTP-ответом при возврате `Python`-объекта из HTTP-обработчика.

## Атрибуты
Атрибуты ответа веб-обработчика используются для управления формированием ответа при возврате любого `python`-объекта из обработчика.

!!! tip "Rapidy позволяет управлять атрибутами во всех типах обработчиков, включая те, что оформлены в стиле aiohttp."
    ```python hl_lines="12 13"
    {!> ./docs/docs/server/response/handler_response/aiohttp_style_example.py !}
    ```

### path

**path**: `str | None = None` — путь к обработчику на веб-сервере.

```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/path.py !}
```

### allow_head

**allow_head**: `bool = True` — флаг, определяющий, нужно ли добавить метод `head` к существующему обработчику `get`.

```python hl_lines="5"
{!> ./docs/docs/server/response/handler_response/allow_head.py !}
```

### status_code

**status_code**: `int | HTTPStatus = 200` — код состояния по умолчанию, который будет использоваться для ответа.

```python hl_lines="6 13"
{!> ./docs/docs/server/response/handler_response/status_code.py !}
```

### response_validate

**response_validate**: `bool = True` — флаг, определяющий, должна ли выполняться валидация ответа обработчика.

```python hl_lines="5"
{!> ./docs/docs/server/response/handler_response/response_validate.py !}
```

---

### response_type

**response_type**: `Type[Any] | None = ...` — задаёт тип ответа обработчика.
*(Если указан, он будет использоваться для создания `Pydantic`-модели ответа вместо аннотации возврата обработчика.)*

```python hl_lines="6"
{!> ./docs/docs/server/response/handler_response/response_type.py !}
```

!!! note "Этот флаг добавляет гибкость в сериализацию и валидацию тела ответа, но в большинстве случаев вам не потребуется его менять."

---

### response_content_type

**response_content_type**: `str = 'application/json'` — определяет заголовок `Content-Type` и управляет постобработкой ответа.

**response_content_type="application/json"**

При значении `"application/json"` данные преобразуются в JSON с использованием [jsonify(dumps=True)](../../../encoders) и кодируются в соответствии
с [charset](#charset).

```python hl_lines="5 9"
{!> ./docs/docs/server/response/handler_response/response_content_type/json_dict.py !}
```

!!! note ""
    Если переданный объект является строкой (`Response(body="string")`), то, согласно стандарту **JSON**, строка будет экранирована дважды:

    ```python hl_lines="5 9"
    {!> ./docs/docs/server/response/handler_response/response_content_type/json_str.py !}
    ```

**content_type="text/*"**

При значении `"text/*"` *(например, `text/plain`, `text/html` и т. д.)*:

- Если данные имеют тип `str`, они отправляются без изменений.
- В противном случае они преобразуются в строку через [jsonify(dumps=False)](../../../encoders).

```python hl_lines="5 9"
{!> ./docs/docs/server/response/handler_response/response_content_type/text.py !}
```

!!! info ""
    Если после `jsonify(dumps=False)` объект не является строкой, он дополнительно кодируется с помощью [json_encoder](#json_encoder)
    во избежание двойного экранирования.

**content_type="*"**

Для любых других типов (`*`):

- Если данные имеют тип `bytes`, они отправляются без изменений.
- В противном случае они преобразуются в строку через [jsonify(dumps=True)](../../../encoders) и кодируются в соответствии с [charset](#charset).

!!! info "Если `content_type` не указан, он устанавливается автоматически на основе типа возвращаемого значения:"
    - `body: dict | BaseModel | dataclass` → `content_type="application/json"`
    - `body: str | Enum | int | float | Decimal | bool` → `content_type="text/plain"`
    - `body: Any` → `content_type="application/octet-stream"`

---

### response_charset

**response_charset**: `str = 'utf-8'` — кодировка, используемая для обработки данных.

```python hl_lines="5"
{!> ./docs/docs/server/response/handler_response/response_charset.py !}
```

---

### response_zlib_executor

**response_zlib_executor**: `Callable | None = None` — функция для сжатия ответа с использованием `zlib`.

??? note "Подробнее о `zlib_executor`"
    `zlib_executor` является частью `aiohttp`.
    Подробнее можно узнать **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

---

### response_zlib_executor_size

**response_zlib_executor_size**: `int | None = None` — размер тела ответа в байтах, при котором будет применяться `zlib`-сжатие.

---

### response_include_fields

**response_include_fields**: `set[str] | dict[str, Any] | None = None` — параметр `include` для Pydantic-моделей, определяющий, какие поля включать в ответ.

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_include_fields.py !}
```

---

### response_exclude_fields

**response_exclude_fields**: `set[str] | dict[str, Any] | None = None` — параметр `exclude` для Pydantic-моделей, определяющий, какие поля исключать из ответа.

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_exclude_fields.py !}
```

---

### response_by_alias

**response_by_alias**: `bool = True` — параметр Pydantic `by_alias`, определяющий, следует ли использовать псевдонимы полей вместо их оригинальных имен.

```python hl_lines="9"
{!> ./docs/docs/server/response/handler_response/response_by_alias/true.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_by_alias/false.py !}
```

---

### response_exclude_unset

**response_exclude_unset**: `bool = False` — параметр Pydantic `exclude_unset`, исключающий из ответа поля, не заданные явно (оставшиеся со значениями
по умолчанию).

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_exclude_unset/false.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_exclude_unset/true.py !}
```

---

### response_exclude_defaults

**response_exclude_defaults**: `bool = False` — параметр Pydantic `exclude_defaults`, исключающий из ответа поля, чьи значения совпадают с значениями
по умолчанию, даже если они были явно установлены.

```python hl_lines="9"
{!> ./docs/docs/server/response/handler_response/response_exclude_defaults/false.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_exclude_defaults/true.py !}
```

---

### response_exclude_none

**response_exclude_none**: `bool = False` — параметр Pydantic `exclude_none`, исключающий из ответа поля со значением `None`.

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_exclude_none/false.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_exclude_none/true.py !}
```

---

### response_custom_encoder

**response_custom_encoder**: `Dict[Any, Callable[Any], Any]] | None = None` — параметр Pydantic `custom_encoder`, задающий пользовательский кодировщик данных.

---

### response_json_encoder

**response_json_encoder**: `Callable = json.dumps` — вызываемый объект, принимающий данные и возвращающий их строковое представление в формате JSON.
Используется при `json_response(dumps=True, ...)`.

```python hl_lines="9"
{!> ./docs/docs/server/response/handler_response/response_json_encoder.py !}
```
