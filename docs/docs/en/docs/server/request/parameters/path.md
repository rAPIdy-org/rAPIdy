# Path
This section explains how to extract and validate path parameters in **`Rapidy`**.

!!! note "You can validate data using any type supported by `pydantic`."

## Description
**Path parameters** allow you to create **dynamic routes** in your application.

You can define path parameters using Python's formatted string syntax:

```Python hl_lines="1"
{!> ./docs/docs/server/request/parameters/path/01_index.py !}
```

!!! note "For more details on dynamic routes in `aiohttp`, see **<a href="https://docs.aiohttp.org/en/stable/web_quickstart.html#aiohttp-web-variable-handler" target="_blank">here</a>**."

## Extracting a Single Path Parameter
`PathParam` allows you to extract a single **path parameter**.

```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/01_path.py !}
```
```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/02_paths.py !}
```

## Extracting All Path Parameters
`PathParams` allows you to extract all **path parameters** at once.

### Extraction into a Predefined Schema

#### pydantic.BaseModel
```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` is supported as a model type, but setting an `alias`
    using standard `dataclasses` tools is not possible.

```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/04_dataclass.py !}
```

### Extraction into a Dictionary
```Python
{!> ./docs/docs/server/request/parameters/path/02_extract/05_dict.py !}
```

## Extraction Without Validation
!!! warning "Disabling validation is not recommended."
    If validation is disabled, parameters are returned in the base `aiohttp` structure:

    - `PathParam` → `str`
    - `PathParams` → `dict[str, str]`

### Ways to Disable Validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/path/03_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/path/03_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If the type is not specified, `Any` is used by default.
```python
{!> ./docs/docs/server/request/parameters/path/03_ignore_validation/03_no_type.py !}
```

## Default Values

!!! warning "`PathParam` and `PathParams` do not support default values."
    This is an intentional architectural limitation:
    without it, dynamic routing cannot be properly implemented.

!!! warning ""
    Attempting to set `default` or `default_factory` for a path parameter
    will raise a `ParameterCannotUseDefaultError` or `ParameterCannotUseDefaultFactoryError` exception.

## Warnings and Specifics

### Using `PathParam` and `PathParams` together

!!! warning "You cannot use `Header` and `Headers` in the same handler."

```python
{!> ./docs/docs/server/request/parameters/path/04_diff_types.py !}
```

When the application starts, an `AnotherDataExtractionTypeAlreadyExistsError` exception will be raised.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already used in the handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `path_data`
------------------------------
```

### The `alias` Attribute for `PathParams`

!!! note "The `alias` attribute does not work for `PathParams()`."

```python
{!> ./docs/docs/server/request/parameters/path/05_alias.py !}
```

## How Raw Data is Extracted

In `Rapidy`, the `match_info` method of the `Request` object is used,
after which the obtained data is passed to `pydantic` for validation.

!!! info "How Extraction Works Inside `Rapidy`"

    ```python
    {!> ./docs/docs/server/request/parameters/path/06_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms."
    For more information about the `aiohttp.Request` object and data extraction methods, see
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.
