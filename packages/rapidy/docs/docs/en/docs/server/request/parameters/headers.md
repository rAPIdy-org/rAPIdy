# Headers
This section covers how to extract and validate headers using **`Rapidy`**.

!!! note "You can validate the data using any type supported by `pydantic`."

## Description
**HTTP headers** allow the client and server to exchange additional information in HTTP requests and responses.

## Extracting a Single Header
`Header` allows you to retrieve a specific header.

```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/01_header.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/02_headers.py !}
```

## Extracting All Headers
`Headers` allows you to extract all headers at once.

### Extracting into a Predefined Schema

#### pydantic.BaseModel
```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` is supported as a model type, but you cannot set an `alias` using standard `dataclasses` tools.

```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/04_dataclass.py !}
```

### Extracting into a Dictionary
```python
{!> ./docs/docs/server/request/parameters/headers/01_extract/05_dict.py !}
```

## Extracting Without Validation
!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will return the basic `aiohttp` structure:

    - `Header` → `str`
    - `Headers` → `CIMultiDictProxy[str]`

### Ways to Disable Validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/headers/02_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/headers/02_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If the type is not specified, it defaults to `Any`.
```python
{!> ./docs/docs/server/request/parameters/headers/02_ignore_validation/03_no_type.py !}
```

## Default Values

The default value for `Header` is used if the request does not contain a header with the specified name.

The default value for `Headers` is used if the request contains no headers at all.

!!! note "A default value for `Headers` is practically never used."
    Any HTTP client will always send basic headers, making this case nearly impossible.
    However, if it ever happens, it will work as expected.

### Using `default`
```python
{!> ./docs/docs/server/request/parameters/headers/03_default/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/03_default/02_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/03_default/03_example.py !}
```

### Using `default_factory`
```python
{!> ./docs/docs/server/request/parameters/headers/04_default_factory/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/headers/04_default_factory/02_example.py !}
```

!!! warning "You cannot use `default` and `default_factory` at the same time."
    Attempting to specify both will raise a `pydantic` exception:
    ```python
    TypeError('cannot specify both default and default_factory')
    ```

## Warnings and Considerations

### Using `Header` and `Headers` together
!!! warning "You cannot use `Header` and `Headers` in the same handler."
```python
{!> ./docs/docs/server/request/parameters/headers/05_diff_types.py !}
```

When the application starts, an `AnotherDataExtractionTypeAlreadyExistsError` exception will be raised.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already use in handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `headers_data`
------------------------------
```

### The `alias` Attribute in `Headers`

!!! note "The `alias` attribute does not work in the `Headers()` parameter."
```python
{!> ./docs/docs/server/request/parameters/headers/06_alias.py !}
```

## How Raw Data is Extracted

`Rapidy` uses the `headers` method of the `Request` object and then passes the retrieved data to a `pydantic` model for validation.

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/headers/07_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms."
    For more details on the `aiohttp.Request` object and data extraction methods, see
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.
