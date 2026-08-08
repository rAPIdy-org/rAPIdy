# JSON
Reading the request body as `JSON`.

## Description
**JSON** (JavaScript Object Notation) *(MIME-type: `application/json`)* is a text-based format for exchanging structured data, based on JavaScript. Today, JSON is language-independent and is used in various programming languages.

This section will show how to extract `JSON` from the request body and validate it using **`Rapidy`**.

## Data Types in JSON

### Object
An unordered set of key-value pairs.
```json
{
    "username": "User",
    "password": "myAwesomePass"
}
```
```python
{!> ./docs/docs/server/request/parameters/body/json/01_obj/example.py !}
```
??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/01_obj/curl.sh !}
    ```

### Array
```json
[
    {"username": "User1", "password": "myAwesomePass1"},
    {"username": "User2", "password": "myAwesomePass2"}
]
```
```python
{!> ./docs/docs/server/request/parameters/body/json/02_array/example.py !}
```
??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/02_array/curl.sh !}
    ```

### Number
An integer or floating-point value.
```json
111
```
```python
{!> ./docs/docs/server/request/parameters/body/json/03_num/example.py !}
```
??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/03_num/curl.sh !}
    ```
!!! note "When sending a string in JSON format, additional escaping is required: `"111"`"

### Literals
`true` (boolean true), `false` (boolean false), and `null` (absence of a value).
```json
true
false
null
```
```python
{!> ./docs/docs/server/request/parameters/body/json/04_literal/example.py !}
```
??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/04_literal/curl_true.sh !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/04_literal/curl_false.sh !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/04_literal/curl_null.sh !}
    ```

### String
```json
"SomeString"
```
```python
{!> ./docs/docs/server/request/parameters/body/json/05_str/example.py !}
```
??? example "Sending with `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/json/05_str/curl.sh !}
    ```
!!! note "When sending a string in JSON format, escaping is required: `\"SomeString\"`"

---

## Custom JSON Decoder
By default, `Rapidy` uses `json.loads` without parameters to decode incoming JSON.

!!! example "Equivalent examples:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/01_default_decoder.py !}
    ```
    or
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/02_default_decoder.py !}
    ```

To use a custom decoder, pass a callable object that takes a `str` as the `json_decoder` parameter.

!!! note "Expected type: `Callable[[str], Any]`"

!!! example "Example with a custom decoder:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/03_custom_decoder.py !}
    ```

If you need to use `json.loads` with parameters, use `functools.partial`:
```python
{!> ./docs/docs/server/request/parameters/body/json/06_json_decoder/04_decoder_with_params.py !}
```

---

## Extraction Without Validation

!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will contain data in the form it was unpacked by the JSON decoder.

### Ways to Disable Validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/body/json/07_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/body/json/07_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If no type is specified, `Any` will be set by default.
```python
{!> ./docs/docs/server/request/parameters/body/json/07_ignore_validation/03_no_type.py !}
```

---

## Default Values
If an HTTP request does not contain a body, the parameter will receive the specified default value (if set).

### Usage Examples

#### Default Value Specified
```python
{!> ./docs/docs/server/request/parameters/body/json/08_default/01_default_exists.py !}
```

#### Optional Request Body
```python
{!> ./docs/docs/server/request/parameters/body/json/08_default/02_default_optional.py !}
```

---

## Extracting Raw Data
`Rapidy` uses the `json` method of the `Request` object to obtain data and passes it to `Pydantic` for validation.

If the data cannot be extracted as JSON, an `ExtractError` will be returned:
```json
{
    "errors": [
        {
            "type": "ExtractError",
            "loc": [
                "body"
            ],
            "msg": "Failed to extract body data as Json: <error_description>"
        }
    ]
}
```

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/01_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms for data extraction."
    More details about the `aiohttp.Request` object and methods for extracting data from it can be found
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.

If a parameter is annotated as `bytes` or `StreamReader`, data is extracted differently.

!!! note "More details about the `StreamReader` object can be found **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">here</a>**."

### `bytes`
```python
{!> ./docs/docs/server/request/parameters/body/json/09_extract_data/02_extract_bytes/01_handler_example.py !}
```
??? info "`Rapidy` Internal Code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/02_extract_bytes/02_rapidy_code.py !}
    ```

### `StreamReader`
```python
{!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/01_handler_example.py !}
```
??? info "`Rapidy` Internal Code"
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/02_rapidy_code.py !}
    ```

!!! warning "Validation with `Pydantic` is not supported for `StreamReader`."

??? warning "A default value cannot be set for `StreamReader`."
    If you attempt to set a default value for `Body` with a `StreamReader` annotation using `default` or `default_factory`,
    a `ParameterCannotUseDefaultError` will be raised.
    ```python
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/json/09_extract_data/03_extract_stream_reader/03_stream_reader_cant_default_text.txt !}
    ```
