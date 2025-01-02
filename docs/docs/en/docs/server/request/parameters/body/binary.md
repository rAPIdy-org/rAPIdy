# Binary
Reading the request body as a byte sequence.

## Description
**Binary** (MIME-type: `application/octet-stream`) — a binary data type.

!!! info "`Rapidy` allows extracting any data with `content_type` as a sequence of bytes."
    Simply annotate it as `bytes` or `StreamReader`.

    !!! tip "Why is this useful?"
        This is useful when you need to explicitly restrict the type of received data and then process it in binary format.

!!! info "There are only two data types that can be extracted regardless of `content_type`: `bytes` and `StreamReader`."

---

## bytes
```python
{!> ./docs/docs/server/request/parameters/body/binary/01_extract_bytes.py !}
```

## StreamReader
!!! note "You can learn more about the `StreamReader` object **<a href='https://docs.aiohttp.org/en/stable/streams.html' target='_blank'>here</a>**."

```python
{!> ./docs/docs/server/request/parameters/body/binary/02_extract_stream_reader.py !}
```

---

## Extraction without validation

!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will contain the base `aiohttp` structure:

    - `Body(content_type=ContentType.text_plain)` → `bytes`

!!! warning "`pydantic` validation does not work for `StreamReader`."

### Ways to disable validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/body/binary/03_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/body/binary/03_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If no type is specified, `Any` will be set by default.
```python
{!> ./docs/docs/server/request/parameters/body/binary/03_ignore_validation/03_no_type.py !}
```

---

## Default values
If the HTTP request body is not provided, a default value *(if set)* will be used.

### Usage Examples

#### Default Value Specified
```python
{!> ./docs/docs/server/request/parameters/body/binary/04_default/01_default_exists.py !}
```

#### Optional Request Body
```python
{!> ./docs/docs/server/request/parameters/body/binary/04_default/02_default_optional.py !}
```

??? warning "A default value cannot be set for `StreamReader`."
    Attempting to set a default value for `StreamReader` using `default` or `default_factory` will raise a `ParameterCannotUseDefaultError`.
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/04_default/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/binary/04_default/03_stream_reader_cant_default_text.txt !}
    ```

---

## How raw data is extracted
!!! note "`Rapidy` uses built-in `aiohttp` data extraction mechanisms."
    You can learn more about the `aiohttp.Request` object and its data extraction methods **<a href='https://docs.aiohttp.org/en/stable/web_reference.html' target='_blank'>here</a>**.

### bytes
`Rapidy` calls the `read` method on the `Request` object and then passes the retrieved data to `pydantic` for validation.

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/05_rapidy_extract_data_binary.py !}
    ```

### StreamReader
`Rapidy` accesses the `content` attribute of the `Request` object and passes it directly to the request handler, bypassing `pydantic` validation.

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/06_rapidy_extract_data_stream_reader.py !}
    ```
