# Body
This section will demonstrate how to extract and validate the `body` using **`Rapidy`**.

## Description
The **HTTP request body** is the part of the request that transmits data from the client to the server. It plays a key role in the `POST`, `PUT`, and `PATCH` methods, which are used to create, update, and modify resources.

For example, in a `POST` request to create a user account, the user data is sent in the request body.

```python
{!> ./docs/docs/server/request/parameters/body/index/01_index.py !}
```

---

## Body Attributes

### `content_type`
```python
# `application/json` by default
content_type: str | ContentType = ContentType.json
```
Defines the expected data type in the `body` that the server accepts.

!!! tip "More details about `enum ContentType` can be found **[here](../../../../enums/index.md)**."

`Rapidy` uses the specified `content_type` to extract data correctly.

!!! info "Supported content types:"
    - `application/json`
    - `application/x-www-form-urlencoded`
    - `multipart/form-data`
    - `text/*` — any MIME type for textual data
    - `application/octet-stream`

    !!! warning ""
        If the server expects a format that `Rapidy` does not explicitly support (e.g., `video/mpeg`), the data will be extracted as `bytes` and passed to the `pydantic` model without processing.

---

### `check_content_type`
Determines whether the `Content-Type` header should be validated.

- When `True` *(default value)*, `Rapidy` will compare the received `Content-Type` header with the expected `content_type`.
  If they do not match, an error will be returned to the client:

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
Allows specifying a custom `json_decoder` for processing JSON data in the request body.

!!! note "Works only when `content_type="application/json"`."

By default, `Rapidy` uses `json.loads` without parameters.

!!! example "Equivalent examples:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/01_default_decoder.py !}
    ```
    or
    ```python
    {!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/02_default_decoder.py !}
    ```

To customize JSON decoding, pass any callable object that accepts a `str` to `json_decoder`.

!!! note "Expected data type: `Callable[[str], Any]`."

!!! example "Example with a custom decoder:"
    ```python
    {!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/03_custom_decoder.py !}
    ```

To use `json.loads` with parameters or a decoder with arguments, use `functools.partial`:

```python
{!> ./docs/docs/server/request/parameters/body/index/02_json_decoder/04_decoder_with_params.py !}
```

---

## Extraction Without Validation
Most `Body` types support data extraction without validation.

!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will contain the base `aiohttp` structure:

    !!! note "More details can be found in the **Extraction Without Validation** section for each `body` type."

### Ways to Disable Validation:

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/body/index/03_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/body/index/03_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If no type is specified, `Any` will be used by default.
```python
{!> ./docs/docs/server/request/parameters/body/index/03_ignore_validation/03_no_type.py !}
```

---

## Default Values
Most `Body` types support default values.

If an HTTP request does not contain a body, the parameter will receive the specified default value (if set).

### Usage Examples

#### Default Value Specified
```python
{!> ./docs/docs/server/request/parameters/body/index/04_default/01_default_exists.py !}
```

#### Optional Request Body
```python
{!> ./docs/docs/server/request/parameters/body/index/04_default/02_default_optional.py !}
```

!!! note "More details can be found in the **Default Values** section for each `body` type."
