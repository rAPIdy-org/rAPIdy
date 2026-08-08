# Query Parameters
This section explains how to extract and validate query parameters using **`Rapidy`**.

!!! note "Remember, you can validate data using any type supported by `pydantic`."

## Description
**Query parameters** are key-value pairs that appear after the <span class="green-color">?</span> in a URL, separated by <span class="green-color">&</span>.

!!! example "Example of a URL with a query string containing three parameters."
    https://www.rapidy.com/search<span class="green-color">?</span><span class="base-color">query</span>=<span class="note-color">database+tools</span><span class="green-color">&</span><span class="base-color">star_rating</span>=<span class="note-color">4</span><span class="green-color">&</span><span class="base-color">order</span>=<span class="note-color">alphabetical</span>

## Extracting a Single QueryParam
`QueryParam` extracts a single **query parameter** by its name.

```python
{!> ./docs/docs/server/request/parameters/query/01_extract/01_query_param.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/01_extract/02_query_params.py !}
```

## Extracting All QueryParams

`QueryParams` extracts all **query parameters** at once.

!!! note "You can validate the data using any type supported by `pydantic`."

### Extracting into a Predefined Schema

#### pydantic.BaseModel
```Python
{!> ./docs/docs/server/request/parameters/query/01_extract/03_base_model.py !}
```

#### dataclasses.dataclass
!!! note ""
    `dataclasses.dataclass` is supported as a model type, but you cannot set an `alias` using standard `dataclasses` tools.

```Python
{!> ./docs/docs/server/request/parameters/query/01_extract/04_dataclass.py !}
```

### Extracting into a Dictionary
```Python
{!> ./docs/docs/server/request/parameters/query/01_extract/05_dict.py !}
```

## Extraction Without Validation
!!! warning "Disabling validation is not recommended."
    If validation is disabled, parameters will be returned in the base `aiohttp` structure:

    - `QueryParam` → `str`
    - `QueryParams` → `MultiDictProxy[str]`

### Ways to Disable Validation

#### Explicit Disabling
```python
{!> ./docs/docs/server/request/parameters/query/02_ignore_validation/01_validate_attr_false.py !}
```

#### Using `Any`
```python
{!> ./docs/docs/server/request/parameters/query/02_ignore_validation/02_any_type.py !}
```

#### No Type Annotation
If the type is not specified, it defaults to `Any`.
```python
{!> ./docs/docs/server/request/parameters/query/02_ignore_validation/03_no_type.py !}
```

## Default Values

The default value for `QueryParam` is used if the incoming request does not contain the specified query parameter.

The default value for `QueryParams` is used if the request does not contain any query parameters.

### Using `default`
```python
{!> ./docs/docs/server/request/parameters/query/03_default/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/03_default/02_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/03_default/03_example.py !}
```

### Using `default_factory`
```python
{!> ./docs/docs/server/request/parameters/query/04_default_factory/01_example.py !}
```
```python
{!> ./docs/docs/server/request/parameters/query/04_default_factory/02_example.py !}
```

!!! warning "You cannot use both `default` and `default_factory` at the same time."
    Attempting to set both will raise a `pydantic` exception:
    ```python
    TypeError('cannot specify both default and default_factory')
    ```

## Warnings and Specifics

### Using `QueryParam` and `QueryParams` Together

!!! warning "You cannot use `QueryParam` and `QueryParams` together in the same handler."
```python
{!> ./docs/docs/server/request/parameters/query/05_diff_types.py !}
```

When the application starts, an `AnotherDataExtractionTypeAlreadyExistsError` exception will be raised.

```
------------------------------
Attribute with this data extraction type cannot be added to the handler - another data extraction type is already used in the handler.

Handler path: `main.py`
Handler name: `handler`
Attribute name: `headers_data`
------------------------------
```

### The `alias` Attribute in `Headers`

!!! note "The `alias` attribute does not work in `QueryParams()`."

```python
{!> ./docs/docs/server/request/parameters/query/06_alias.py !}
```

## How Raw Data is Extracted

`Rapidy` uses the `rel_url.query` method of the `Request` object and then passes the retrieved data to a `pydantic` model for validation.

!!! info "How Extraction Works Inside `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/query/07_extract_raw.py !}
    ```

!!! note "`Rapidy` uses built-in `aiohttp` mechanisms."
    For more details on the `aiohttp.Request` object and data extraction methods, see
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">here</a>**.
