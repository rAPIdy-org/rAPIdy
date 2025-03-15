# X-WWW-Form-Urlencoded
Reading the request body as `application/x-www-form-urlencoded`.

## Description
**X-WWW-Form-Urlencoded** *(MIME-type: `application/x-www-form-urlencoded`)* is a widely used content type for transmitting data through HTML forms on the internet.

The format represents a string with key-value pairs as follows:
`key1=value1&key2=value2`.

```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/01_index/example.py !}
```

??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/01_index/curl.sh !}
    ```

## Extracting Without Validation

!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will contain a basic `aiohttp` structure:

    - `Body(content_type=ContentType.x_www_form)` → `MultiDictProxy[str]`

### Ways to Disable Validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/02_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/02_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If no type is specified, `Any` will be set by default.
```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/02_ignore_validation/03_no_type.py !}
```

## Default Values

If the HTTP request does not contain a body, the parameter will receive the specified default value (if provided).

### Usage Examples

#### Default Value Specified
```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/03_default/01_default_exists.py !}
```

#### Optional Request Body
```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/03_default/02_default_optional.py !}
```

## Extracting Raw Data
`Rapidy` uses the `post` method of the `Request` object to retrieve data and passes it to `Pydantic` for validation.

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/04_extract_data/01_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms."
    For more information about the `aiohttp.Request` object and data extraction methods, see
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

!!! note "`x-www-form-urlencoded` and `multipart/form-data` are handled the same way."
    Both data types are extracted using the `post` method of the `Request` object. This is a characteristic of `aiohttp` implementation.

If a parameter is annotated as `bytes` or `StreamReader`, data is extracted differently.

!!! note "For more details on the `StreamReader` object, see **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">here</a>**."

### `bytes`
```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/04_extract_data/02_extract_bytes/01_handler_example.py !}
```
??? info "`Rapidy` Internal Code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/04_extract_data/02_extract_bytes/02_rapidy_code.py !}
    ```

### `StreamReader`
```python
{!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/04_extract_data/03_extract_stream_reader/01_handler_example.py !}
```
??? info "`Rapidy` Internal Code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/04_extract_data/03_extract_stream_reader/02_rapidy_code.py !}
    ```

!!! warning "Validation with `Pydantic` is not supported for `StreamReader`."

??? warning "Default values cannot be set for `StreamReader`."
    If you attempt to set a default value for `Body` with a `StreamReader` annotation using `default` or `default_factory`,
    a `ParameterCannotUseDefaultError` will be raised.

    ```python
    {!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/x_www_form_urlencoded/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default_text.txt !}
    ```
