# Multipart Form Data
Reading the request body as `multipart/form-data`.

## Description
**Form Data** *(MIME-type: `multipart/form-data`)* is one of the most commonly used content types for sending **binary** data to a server.

The *multipart* format means that data is sent to the server in separate parts.
Each part can have its own content type, filename, and data.
Data is separated using a boundary string.

```python
{!> ./docs/docs/server/request/parameters/body/multipart/01_index/example.py !}
```

!!! example "Data Example"
    ```text
    {!> ./docs/docs/server/request/parameters/body/multipart/01_index/raw_example.txt !}
    ```

??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/multipart/01_index/curl.sh !}
    ```

---

## Extraction Without Validation

!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will contain the base `aiohttp` structure:

    - `Body(content_type=ContentType.m_part_form_data) → MultiDictProxy[Union[str, bytes, FileField]]`

### Ways to Disable Validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/body/multipart/02_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/body/multipart/02_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If no type is specified, `Any` will be set by default.
```python
{!> ./docs/docs/server/request/parameters/body/multipart/02_ignore_validation/03_no_type.py !}
```

---

## Default Values
If an HTTP request does not contain a body, the parameter will receive the specified default value (if set).

### Usage Examples

#### Default Value Specified
```python
{!> ./docs/docs/server/request/parameters/body/multipart/03_default/01_default_exists.py !}
```

#### Optional Request Body
```python
{!> ./docs/docs/server/request/parameters/body/multipart/03_default/02_default_optional.py !}
```

---

## Extracting Raw Data
`Rapidy` uses the `post` method of the `Request` object to obtain data and passes it to `Pydantic` for validation.

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/01_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms for data extraction."
    More details about the `aiohttp.Request` object and methods for extracting data from it can be found
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

!!! note "`x-www-form-urlencoded` and `multipart/form-data` are processed the same way."
    Both of these content types are extracted using the `post` method of the `Request` object. This is a feature of `aiohttp`.

If a parameter is annotated as `bytes` or `StreamReader`, data is extracted differently.

!!! note "More details about the `StreamReader` object can be found **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">here</a>**."

### `bytes`
```python
{!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/02_extract_bytes/01_handler_example.py !}
```
??? info "`Rapidy` Internal Code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/02_extract_bytes/02_rapidy_code.py !}
    ```

### `StreamReader`
```python
{!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/01_handler_example.py !}
```
??? info "`Rapidy` Internal Code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/02_rapidy_code.py !}
    ```

!!! warning "Validation with `Pydantic` is not supported for `StreamReader`."

??? warning "Default values cannot be set for `StreamReader`."
    If you attempt to set a default value for `Body` with a `StreamReader` annotation using `default` or `default_factory`,
    a `ParameterCannotUseDefaultError` will be raised.
    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default_text.txt !}
    ```
