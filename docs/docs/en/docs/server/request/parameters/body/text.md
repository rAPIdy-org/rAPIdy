# Text
Reading the request body as a string.

## Description
**Text** *(MIME-type: `text/*`)* is a data type representing a string.

!!! info "`Rapidy` works with any text, regardless of its `subtype`."
    Examples: `text/plain`, `text/html`, `text/css`, `text/xml`, `...`, `text/*`.

!!! info "Character encoding detection"
    The `charset` parameter of the `Content-Type` header is used for text decoding.
    If `charset` is not specified by the client, the text will be decoded using `utf-8`.

```python
{!> ./docs/docs/server/request/parameters/body/text/01_index/example.py !}
```

??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/text/01_index/curl.sh !}
    ```

---

## Extraction without validation

!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will contain the basic `aiohttp` structure:

    - `Body(content_type=ContentType.text_plain)` → `str`

### Ways to disable validation

#### Explicit disabling
```python
{!> ./docs/docs/server/request/parameters/body/text/02_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/body/text/02_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If no type is specified, `Any` will be set by default.
```python
{!> ./docs/docs/server/request/parameters/body/text/02_ignore_validation/03_no_type.py !}
```

---

## Default values
If an HTTP request does not contain a body, the parameter will receive the specified default value (if set).

### Usage examples

#### Default Value Specified
```python
{!> ./docs/docs/server/request/parameters/body/text/03_default/01_default_exists.py !}
```

#### Optional Request Body
```python
{!> ./docs/docs/server/request/parameters/body/text/03_default/02_default_optional.py !}
```

---

## Extracting Raw Data
`Rapidy` uses the `text` method of the `Request` object to retrieve data and passes it to `Pydantic` for validation.

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/text/04_extract_data/01_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms for data extraction."
    More details about the `aiohttp.Request` object and methods for extracting data from it can be found
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

If a parameter is annotated as `bytes` or `StreamReader`, data is extracted differently.

!!! note "More details about the `StreamReader` object can be found **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">here</a>**."

### `bytes`
```python
{!> ./docs/docs/server/request/parameters/body/text/04_extract_data/02_extract_bytes/01_handler_example.py !}
```

??? info "`Rapidy` internal code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/text/04_extract_data/02_extract_bytes/02_rapidy_code.py !}
    ```

### `StreamReader`
```python
{!> ./docs/docs/server/request/parameters/body/text/04_extract_data/03_extract_stream_reader/01_handler_example.py !}
```

??? info "`Rapidy` Internal Code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/text/04_extract_data/03_extract_stream_reader/02_rapidy_code.py !}
    ```

!!! warning "Validation with `Pydantic` is not supported for `StreamReader`."

??? warning "A default value cannot be set for `StreamReader`."
    If you try to set a default value for `Body` annotated with `StreamReader` using `default` or `default_factory`, an error `ParameterCannotUseDefaultError` will be raised.
    ```python
    {!> ./docs/docs/server/request/parameters/body/text/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/text/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default_text.txt !}
    ```
