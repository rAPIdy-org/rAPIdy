# Cookies
This section explains how to extract and validate cookies using **`Rapidy`**.

!!! note "You can validate the data using any type supported by `pydantic`."

## Description
A **cookie** is a small set of user data stored on their device without modifications or processing.

The web client sends this data to the web server as part of an HTTP request each time it accesses the corresponding website.


## Extracting a Single Cookie
`Cookie` allows retrieving a specific **cookie** by its name.

```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/01_cookie.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/02_cookies.py !}
```

## Extracting All Cookies
`Cookies` allows retrieving all **cookies** at once.

### Extracting into a Predefined Schema

#### pydantic.BaseModel
```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` is supported as a model type, but it is not possible to set an `alias` using standard `dataclasses` tools.

```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/04_dataclass.py !}
```

### Extracting into a Dictionary
```python
{!> ./docs/docs/server/request/parameters/cookies/01_extract/05_dict.py !}
```

## Extracting Without Validation

!!! warning "Disabling validation is not recommended."
    If validation is disabled, the parameter will return a basic `aiohttp` structure:

    - `Cookie` → `str`
    - `Cookies` → `Mapping[str, str]`

### Ways to Disable Validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/cookies/02_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/cookies/02_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If no type is specified, it defaults to `Any`.
```python
{!> ./docs/docs/server/request/parameters/cookies/02_ignore_validation/03_no_type.py !}
```

## Default Values

The default value for `Cookie` will be used if no cookie with the specified name is found in the request.

The default value for `Cookies` will be used if no cookies are found in the request.

### Using `default`
```python
{!> ./docs/docs/server/request/parameters/cookies/03_default/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/03_default/02_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/03_default/03_example.py !}
```

### Using `default_factory`
```python
{!> ./docs/docs/server/request/parameters/cookies/04_default_factory/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/cookies/04_default_factory/02_example.py !}
```

!!! warning "You cannot use `default` and `default_factory` simultaneously."
    Attempting to specify both will raise a `pydantic` exception:
    ```python
    TypeError('cannot specify both default and default_factory')
    ```

## Warnings and Considerations

### Using `Cookie` and `Cookies` together
!!! warning "It is not possible to use `Cookie` and `Cookies` in the same handler."
```python
{!> ./docs/docs/server/request/parameters/cookies/05_diff_types.py !}
```

When the application starts, an `AnotherDataExtractionTypeAlreadyExistsError` exception will be raised.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already in use.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `cookie_data`
------------------------------
```

### The `alias` Attribute in `Cookies`

!!! note "The `alias` attribute does not work in the `Cookies()` parameter."
```python
{!> ./docs/docs/server/request/parameters/cookies/06_alias.py !}
```

## How Raw Data Is Extracted

`Rapidy` uses the `cookies` method of the `Request` object and then passes the retrieved data to a `pydantic` model for validation.

!!! info "How data extraction works in `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/cookies/07_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms for data extraction."
    More details about the `aiohttp.Request` object and methods for extracting data from it can be found
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.
