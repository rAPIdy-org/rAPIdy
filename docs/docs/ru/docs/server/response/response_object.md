# Объект управления HTTP-ответом
Для управления HTTP-ответами `Rapidy` использует объект `Response`.

```python
{!> ./docs/docs/server/response/03_response_import.py !}
```

Для простых сценариев получения или сохранения данных `rapidy.http.Response` может быть не нужен, но если вы хотите гибко управлять ответом вашего
HTTP-обработчика, то данный раздел расскажет о том как это можно делать.

!!! note "Объект `Response` в `Rapidy` является оберткой над `aiohttp.Response`."
    `rapidy.http.Response` в отличие от `aiohttp.Response` стал гораздо более вернеуровневым, у него появилась удобная сериализация данных.

    Подробнее о `aiohttp.Response` можно узнать **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

## Аттрибуты

### body
**body**: `Any | None = None` — тело сообщения *(может быть практически любым объектом)*.

Чтобы задать `body`, создайте объект `Response(body=...)` или используйте сеттер `body` существующего экземпляра.
```python hl_lines="6 12 17"
{!> ./docs/docs/server/response/response_object/03_response_attrs/body/index.py !}
```

Для получения `body` воспользуйтесь геттером `body`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/body/getter.py !}
```

!!! note "Логика подготовки и преобразования данных завязана на аттрибуте [content_type](#content_type)."

!!! note ""
    Объект типа `bytes` будет отправлен как тело без изменений.

!!! info ""
    Если вы хотите, чтобы работали флаги `pydantic`, такие как `exclude_none` и другие, переданный объект должен быть экземпляром `pydantic.BaseModel`.

---

### text
**text**: `Any | None = None` — текстовое тело сообщения *(может быть практически любым объектом)*.

Чтобы задать тело ответа как `text`, создайте объект `Response(text=...)` или используйте сеттер `text` существующего экземпляра.
```python hl_lines="6 12 17"
{!> ./docs/docs/server/response/response_object/03_response_attrs/text/index.py !}
```

Для получения тела ответа как `text` воспользуйтесь геттером `text`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/text/getter.py !}
```

!!! note "Логика подготовки и преобразования данных завязана на аттрибуте [content_type](#content_type)."

!!! note ""
    Объект типа `str` отправляется как тело без проверок (`content_type="text/plain"`).

!!! note "Если данные не `str`, применяется та же логика преобразования данных, что и для [body](#body)."

---

### content_type
**content_type**: `str | ContentType | None = None` — аттрибут позволяющий управлять заголовком `Content-Type`.

Заголовок `Content-Type` сообщает клиенту (браузеру, API-клиенту, другому серверу), какой тип данных содержится в теле HTTP-ответа.

Чтобы задать `content_type`, создайте объект `Response(content_type=...)` или используйте сеттер `content_type` существующего экземпляра.
```python hl_lines="7 9 16 18 24 26"
{!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/index.py !}
```

Для получения `content_type` воспользуйтесь геттером `content_type`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/getter.py !}
```

!!! note "Если указан `content_type`, переданные данные будут преобразованы в соответствии с ним."

!!! note "Если `content_type` не указан - `content_type` будет определен автоматически в зависимости от типа данных которое отдает сервер."

??? example "content_type="application/json"
    `content_type="application/json"` — данные преобразуются в `JSON` с использованием [jsonify(dumps=True)](../../../encoders)
    и кодируются в соответствии с [charset](#charset).

    ```python hl_lines="7"
    {!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/json_dict.py !}
    ```

    !!! note ""
        Если переданный объект является строкой `Response(body="string")`, то строка, согласно стандарту **JSON**, будет экранирована дважды:
        ```python hl_lines="7"
        {!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/json_str.py !}
        ```

??? example "content_type="text/*"
    `content_type="text/*"` *(любой текстовый тип: `text/plain`, `text/html` и т. д.)* - если данные имеют тип `str`, они отправляются без изменений.
    В противном случае они преобразуются в строку через [jsonify(dumps=False)](../../../encoders).

    ```python hl_lines="7"
    {!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/text.py !}
    ```

    !!! info ""
        Если после `jsonify(dumps=False)` объект не является строкой, он дополнительно преобразуется с помощью [json_encoder](#json_encoder),
        чтобы избежать двойного экранирования.

??? example "content_type - любой другой MIME-type."
    Если данные имеют тип `bytes`, они отправляются без изменений.
    В противном случае они преобразуются в строку с использованием [jsonify(dumps=True)](../../../encoders) и кодируются в соответствии с [charset](#charset).

!!! info "Если `content_type` не указан, он устанавливается автоматически:"

    - `body: dict | BaseModel | dataclass` → `content_type="application/json"`
        ```python
        Response(body={"hello": "rapidy"})
        Response(body=SomeModel(hello="rapidy"))
        ```

    - `body: str | Enum | int | float | Decimal | bool` → `content_type="text/plain"`
        ```python
        Response(body="string")
        Response(body=SomeEnum.string)
        Response(body=1)
        Response(body=1.0)
        Response(body=Decimal("1.0"))
        Response(body=True)
        ```

    - `body: Any` → `content_type="application/octet-stream"`
        ```python
        Response(body=b'bytes')
        Response(body=AnotherType())
        ```
---

### status
**status**: `int = 200` — HTTP-код ответа.

```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/status/index.py !}
```

#### set_status
Для установления `status` воспользуйтесь методом `set_status`, объекта `Response`.

```python hl_lines="5 10"
{!> ./docs/docs/server/response/response_object/03_response_attrs/status/setter.py !}
```

---

### headers
**headers**: `Mapping[str, str] | None = None` — дополнительные заголовки ответа.

```python hl_lines="6 12 17"
{!> ./docs/docs/server/response/response_object/03_response_attrs/headers/index.py !}
```

Для получения `headers` воспользуйтесь геттером `headers`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/headers/getter.py !}
```

---

### cookies
**cookies**: `SimpleCookie | None = None` - файлы cookie ответа для установки их браузером.

Для получения `cookie` воспользуйтесь геттером `cookies`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/cookie/getter.py !}
```

#### set_cookie
Для установления `cookies` воспользуйтесь методом `set_cookie`, объекта `Response`.
```python hl_lines="6 11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/cookie/index.py !}
```

#### del_cookie
Для удаления `cookie` воспользуйтесь методом `del_cookie`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/cookie/delete.py !}
```

---

### charset
**charset**: `str | Charset | None = 'utf-8'` — кодировка, используемая для кодирования и декодирования данных.

Чтобы задать `charset`, создайте объект `Response(charset=...)` или используйте сеттер `charset` существующего экземпляра.
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/charset/index.py !}
```

Для получения `charset` воспользуйтесь геттером `charset`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/charset/getter.py !}
```

---

### last_modified
**last_modified**: `int | float | datetime.datetime | str | None = None` — аттрибут отвечает за управление заголовком `Last-Modified`.

Для установления `last_modified` воспользуйтесь сеттером `last_modified`, объекта `Response`.
```python
{!> ./docs/docs/server/response/response_object/03_response_attrs/last_modified/index.py !}
```

Для получения `last_modified` воспользуйтесь геттером `last_modified`, объекта `Response`.
```python
{!> ./docs/docs/server/response/response_object/03_response_attrs/last_modified/getter.py !}
```

??? example "Полноценный пример построения HTTP-обработчика с использованием last_modified"
    ```python
    {!> ./docs/docs/server/response/response_object/03_response_attrs/last_modified/advanced_example.py !}
    ```

---

### etag
**etag**: `ETag | str` - аттрибут отвечает за управление заголовком `Etag`.

Для установления `etag` воспользуйтесь сеттером `etag`, объекта `Response`.
```python hl_lines="6 11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/etag/index.py !}
```

Для получения `etag` воспользуйтесь геттером `etag`, объекта `Response`.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/etag/getter.py !}
```

??? example "Полноценный пример построения HTTP-обработчика с использованием etag."
    ```python
    {!> ./docs/docs/server/response/response_object/03_response_attrs/etag/advanced_example.py !}
    ```

---

### include
**include**: `set[str] | dict[str, Any] | None = None` — параметр `include` из Pydantic, указывающий, какие поля включать.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/include.py !}
```

---

### exclude
**exclude**: `set[str] | dict[str, Any] | None = None` — параметр `exclude` из Pydantic, указывающий, какие поля исключать.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude.py !}
```

---

### by_alias
**by_alias**: `bool = True` — параметр `by_alias` из Pydantic, определяющий, использовать ли псевдонимы атрибутов при сериализации.

```python hl_lines="11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/by_alias/true.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/by_alias/false.py !}
```

---

### exclude_unset
**exclude_unset**: `bool = False` — параметр `exclude_unset` из Pydantic, исключающий поля, неявно установленные в значение по умолчанию.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_unset/false.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_unset/true.py !}
```

---

### exclude_defaults
**exclude_defaults**: `bool = False` — параметр `exclude_defaults` из Pydantic, исключающий поля, имеющие значение по умолчанию, даже если они были явно заданы.

```python hl_lines="11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_defaults/false.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_defaults/true.py !}
```

---

### exclude_none
**exclude_none**: `bool = False` — параметр `exclude_none` из Pydantic, исключающий из вывода поля со значением `None`.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_none/false.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_none/true.py !}
```

---

### custom_encoder
**custom_encoder**: `Dict[Any, Callable[Any], Any]] | None = None` — параметр `custom_encoder` из Pydantic, позволяющий задать пользовательский кодировщик.

---

### json_encoder
**json_encoder**: `Callable = json.dumps` — функция, принимающая объект и возвращающая его `JSON`-представление.

```python hl_lines="11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/json_encoder.py !}
```
