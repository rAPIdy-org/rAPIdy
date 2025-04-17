# Response object
To manage HTTP responses, `Rapidy` uses the `Response` object.

```python
{!> ./docs/docs/server/response/03_response_import.py !}
```

For simple scenarios of retrieving or saving data, `rapidy.http.Response` may not be required, but if you want to flexibly manage the response of your HTTP handler, this section will explain how to do that.

!!! note "The `Response` object in `Rapidy` is a wrapper around `aiohttp.Response`."
    Unlike `aiohttp.Response`, `rapidy.http.Response` has become much more versatile, and it now has convenient data serialization.

    More about `aiohttp.Response` can be found **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

## Attributes

### body
**body**: `Any | None = None` — the message body *(can be almost any object)*.

To set the `body`, create a `Response(body=...)` object or use the `body` setter of an existing instance.
```python hl_lines="6 12 17"
{!> ./docs/docs/server/response/response_object/03_response_attrs/body/index.py !}
```

To get the `body`, use the `body` getter of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/body/getter.py !}
```

!!! note "The logic for preparing and transforming data is tied to the [content_type](#content_type) attribute."

!!! note ""
    A `bytes` type object will be sent as the body without changes.

!!! info ""
    If you want Pydantic flags, such as `exclude_none` and others, to work, the passed object must be an instance of `pydantic.BaseModel`.

---

### text
**text**: `Any | None = None` — the textual message body *(can be almost any object)*.

To set the response body as `text`, create a `Response(text=...)` object or use the `text` setter of an existing instance.
```python hl_lines="6 12 17"
{!> ./docs/docs/server/response/response_object/03_response_attrs/text/index.py !}
```

To get the response body as `text`, use the `text` getter of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/text/getter.py !}
```

!!! note "The logic for preparing and transforming data is tied to the [content_type](#content_type) attribute."

!!! note ""
    A `str` type object will be sent as the body without checks (`content_type="text/plain"`).

!!! note "If the data is not `str`, the same data transformation logic as for [body](#body) applies."

---

### content_type
**content_type**: `str | ContentType | None = None` — the attribute that allows you to manage the `Content-Type` header.

The `Content-Type` header informs the client (browser, API client, another server) about the type of data contained in the HTTP response body.

To set the `content_type`, create a `Response(content_type=...)` object or use the `content_type` setter of an existing instance.
```python hl_lines="7 9 16 18 24 26"
{!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/index.py !}
```

To get the `content_type`, use the `content_type` getter of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/getter.py !}
```

!!! note "If `content_type` is specified, the provided data will be transformed accordingly."

!!! note "If `content_type` is not specified, the `content_type` will be determined automatically based on the type of data the server is sending."

??? example "content_type="application/json"
    `content_type="application/json"` — the data is converted to `JSON` using [jsonify(dumps=True)](../../../encoders)
    and encoded according to [charset](#charset).

    ```python hl_lines="7"
    {!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/json_dict.py !}
    ```

    !!! note ""
        If the passed object is a string `Response(body="string")`, the string, according to the **JSON** standard, will be double-escaped:
        ```python hl_lines="7"
        {!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/json_str.py !}
        ```

??? example "content_type="text/*"
    `content_type="text/*"` *(any text type: `text/plain`, `text/html`, etc.)* — if the data is of type `str`, it is sent without changes.
    Otherwise, it is transformed into a string using [jsonify(dumps=False)](../../../encoders).

    ```python hl_lines="7"
    {!> ./docs/docs/server/response/response_object/03_response_attrs/content_type/text.py !}
    ```

    !!! info ""
        If after `jsonify(dumps=False)` the object is not a string, it is further transformed using [json_encoder](#json_encoder)
        to avoid double escaping.

??? example "content_type - any other MIME-type."
    If the data is of type `bytes`, it is sent without changes.
    Otherwise, it is transformed into a string using [jsonify(dumps=True)](../../../encoders) and encoded according to [charset](#charset).

!!! info "If `content_type` is not specified, it is set automatically:"

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
**status**: `int = 200` — HTTP response code.

```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/status/index.py !}
```

#### set_status
To set the `status`, use the `set_status` method of the `Response` object.

```python hl_lines="5 10"
{!> ./docs/docs/server/response/response_object/03_response_attrs/status/setter.py !}
```

---

### headers
**headers**: `Mapping[str, str] | None = None` — additional response headers.

```python hl_lines="6 12 17"
{!> ./docs/docs/server/response/response_object/03_response_attrs/headers/index.py !}
```

To get the `headers`, use the `headers` getter of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/headers/getter.py !}
```

---

### cookies
**cookies**: `SimpleCookie | None = None` — response cookies to be set in the browser.

To get the `cookies`, use the `cookies` getter of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/cookie/getter.py !}
```

#### set_cookie
To set `cookies`, use the `set_cookie` method of the `Response` object.
```python hl_lines="6 11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/cookie/index.py !}
```

#### del_cookie
To delete `cookies`, use the `del_cookie` method of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/cookie/delete.py !}
```

---

### charset
**charset**: `str | Charset | None = 'utf-8'` — the encoding used for encoding and decoding data.

To set the `charset`, create a `Response(charset=...)` object or use the `charset` setter of an existing instance.
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/charset/index.py !}
```

To get the `charset`, use the `charset` getter of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/charset/getter.py !}
```

---

### last_modified
**last_modified**: `int | float | datetime.datetime | str | None = None` — the attribute responsible for managing the `Last-Modified` header.

To set `last_modified`, use the `last_modified` setter of the `Response` object.
```python
{!> ./docs/docs/server/response/response_object/03_response_attrs/last_modified/index.py !}
```

To get `last_modified`, use the `last_modified` getter of the `Response` object.
```python
{!> ./docs/docs/server/response/response_object/03_response_attrs/last_modified/getter.py !}
```

??? example "Full example of building an HTTP handler using last_modified"
    ```python
    {!> ./docs/docs/server/response/response_object/03_response_attrs/last_modified/advanced_example.py !}
    ```

---

### etag
**etag**: `ETag | str` — the attribute responsible for managing the `Etag` header.

To set `etag`, use the `etag` setter of the `Response` object.
```python hl_lines="6 11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/etag/index.py !}
```

To get `etag`, use the `etag` getter of the `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/response_object/03_response_attrs/etag/getter.py !}
```

??? example "Full example of building an HTTP handler using etag."
    ```python
    {!> ./docs/docs/server/response/response_object/03_response_attrs/etag/advanced_example.py !}
    ```

---

### include
**include**: `set[str] | dict[str, Any] | None = None` — the `include` parameter from Pydantic, specifying which fields to include.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/include.py !}
```

---

### exclude
**exclude**: `set[str] | dict[str, Any] | None = None` — the `exclude` parameter from Pydantic, specifying which fields to exclude.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude.py !}
```

---

### by_alias
**by_alias**: `bool = True` — the `by_alias` parameter from Pydantic, determining whether to use attribute aliases during serialization.

```python hl_lines="11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/by_alias/true.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/by_alias/false.py !}
```

---

### exclude_unset
**exclude_unset**: `bool = False` — the `exclude_unset` parameter from Pydantic, excluding fields not explicitly set to their default value.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_unset/false.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_unset/true.py !}
```

---

### exclude_defaults
**exclude_defaults**: `bool = False` — the `exclude_defaults` parameter from Pydantic, excluding fields with default values even if they were explicitly set.

```python hl_lines="11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_defaults/false.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_defaults/true.py !}
```

---

### exclude_none
**exclude_none**: `bool = False` — the `exclude_none` parameter from Pydantic, excluding fields with `None` values from the output.

```python hl_lines="12"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_none/false.py !}
```
```python hl_lines="6"
{!> ./docs/docs/server/response/response_object/03_response_attrs/exclude_none/true.py !}
```

---

### custom_encoder
**custom_encoder**: `Dict[Any, Callable[Any], Any]] | None = None` — the `custom_encoder` parameter from Pydantic, allowing you to specify a custom encoder.

---

### json_encoder
**json_encoder**: `Callable = json.dumps` — a function that takes an object and returns its `JSON` representation.

```python hl_lines="11"
{!> ./docs/docs/server/response/response_object/03_response_attrs/json_encoder.py !}
```
