# Handler Response
This section explains how to manage an HTTP response in **`Rapidy`** when returning a `Python` object from an HTTP handler.

## Attributes
Handler response attributes are used to control how a response is generated when returning any `Python` object from a handler.

!!! tip "Rapidy supports attribute management in all types of handlers, including those written in the aiohttp style."
    ```python hl_lines="12 13"
    {!> ./docs/docs/server/response/handler_response/aiohttp_style_example.py !}
    ```

### path

**path**: `str | None = None` — the path to the handler on the web server.

```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/path.py !}
```

### allow_head

**allow_head**: `bool = True` — a flag indicating whether to add the `head` method to an existing `get` handler.

```python hl_lines="5"
{!> ./docs/docs/server/response/handler_response/allow_head.py !}
```

### status_code

**status_code**: `int | HTTPStatus = 200` — the default status code used for the response.

```python hl_lines="6 13"
{!> ./docs/docs/server/response/handler_response/status_code.py !}
```

### response_validate

**response_validate**: `bool = True` — a flag indicating whether the handler response should be validated.

```python hl_lines="5"
{!> ./docs/docs/server/response/handler_response/response_validate.py !}
```

---

### response_type

**response_type**: `Type[Any] | None = ...` — defines the response type of the handler.
*(If specified, this attribute will be used to create a `Pydantic` response model instead of the handler's return annotation.)*

```python hl_lines="6"
{!> ./docs/docs/server/response/handler_response/response_type.py !}
```

!!! note "This flag adds flexibility to response body serialization and validation, but in most cases, you won't need to modify it."

---

### response_content_type

**response_content_type**: `str = 'application/json'` — defines the `Content-Type` header and manages response post-processing.

**response_content_type="application/json"**

When set to `"application/json"`, data is converted to JSON using [jsonify(dumps=True)](../../../encoders) and encoded according to
the [charset](#charset).

```python hl_lines="5 9"
{!> ./docs/docs/server/response/handler_response/response_content_type/json_dict.py !}
```

!!! note ""
    If the provided object is a string (`Response(body="string")`), then according to the **JSON** standard, the string will be double-escaped:

    ```python hl_lines="5 9"
    {!> ./docs/docs/server/response/handler_response/response_content_type/json_str.py !}
    ```

**content_type="text/*"**

When set to `"text/*"` *(e.g., `text/plain`, `text/html`, etc.)*:

- If the data is of type `str`, it is sent as is.
- Otherwise, it is converted to a string using [jsonify(dumps=False)](../../../encoders).

```python hl_lines="5 9"
{!> ./docs/docs/server/response/handler_response/response_content_type/text.py !}
```

!!! info ""
    If the object is not a string after `jsonify(dumps=False)`, it is additionally encoded using [json_encoder](#json_encoder)
    to avoid double escaping.

**content_type="*"**

For any other types (`*`):

- If the data is of type `bytes`, it is sent as is.
- Otherwise, it is converted to a string using [jsonify(dumps=True)](../../../encoders) and encoded according to the [charset](#charset).

!!! info "If `content_type` is not specified, it is set automatically based on the return type annotation:"
    - `body: dict | BaseModel | dataclass` → `content_type="application/json"`
    - `body: str | Enum | int | float | Decimal | bool` → `content_type="text/plain"`
    - `body: Any` → `content_type="application/octet-stream"`

---

### response_charset

**response_charset**: `str = 'utf-8'` — the character set used for encoding and decoding data.

```python hl_lines="5"
{!> ./docs/docs/server/response/handler_response/response_charset.py !}
```

---

### response_zlib_executor

**response_zlib_executor**: `Callable | None = None` — a function used for response compression with `zlib`.

??? note "More about `zlib_executor`"
    `zlib_executor` is a feature of `aiohttp`.
    Learn more **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

---

### response_zlib_executor_size

**response_zlib_executor_size**: `int | None = None` — the response body size (in bytes) at which `zlib` compression is applied.

---

### response_include_fields

**response_include_fields**: `set[str] | dict[str, Any] | None = None` — the Pydantic `include` parameter, specifying which fields to include in the response.

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_include_fields.py !}
```

---

### response_exclude_fields

**response_exclude_fields**: `set[str] | dict[str, Any] | None = None` — the Pydantic `exclude` parameter, specifying which fields to exclude from the response.

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_exclude_fields.py !}
```

---

### response_by_alias

**response_by_alias**: `bool = True` — the Pydantic `by_alias` parameter, determining whether to use field aliases instead of their original names.

```python hl_lines="9"
{!> ./docs/docs/server/response/handler_response/response_by_alias/true.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_by_alias/false.py !}
```

---

### response_exclude_unset

**response_exclude_unset**: `bool = False` — the Pydantic `exclude_unset` parameter, excluding fields from the response that were not explicitly set
(and only have default values).

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_exclude_unset/false.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_exclude_unset/true.py !}
```

---

### response_exclude_defaults

**response_exclude_defaults**: `bool = False` — the Pydantic `exclude_defaults` parameter, excluding fields from the response if their values
match the default values, even if explicitly set.

```python hl_lines="9"
{!> ./docs/docs/server/response/handler_response/response_exclude_defaults/false.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_exclude_defaults/true.py !}
```

---

### response_exclude_none

**response_exclude_none**: `bool = False` — the Pydantic `exclude_none` parameter, excluding fields from the response if they have a value of `None`.

```python hl_lines="10"
{!> ./docs/docs/server/response/handler_response/response_exclude_none/false.py !}
```
```python hl_lines="4"
{!> ./docs/docs/server/response/handler_response/response_exclude_none/true.py !}
```

---

### response_custom_encoder

**response_custom_encoder**: `Callable | None = None` — the Pydantic `custom_encoder` parameter, specifying a custom data encoder.

---

### response_json_encoder

**response_json_encoder**: `Callable = json.dumps` — a callable that takes an object and returns its JSON string representation.
Used when `json_response(dumps=True, ...)` is applied.

```python hl_lines="9"
{!> ./docs/docs/server/response/handler_response/response_json_encoder.py !}
```
