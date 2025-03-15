# Parameters
In this section, we will explore how to extract and validate HTTP parameters using **`Rapidy`**.

## Basics of Data Extraction and Validation
To validate and extract data from an incoming HTTP request, **Rapidy** uses its internal data types — **rapidy parameters**.

The example below extracts and validates a **dynamic path variable** `user_id` and the **header** `Host`:

```python
{!> ./docs/docs/server/request/parameters/index/01_index.py !}
```

### What is a rapidy parameter?

A **rapidy parameter** is a `meta-object` that contains information on how parameters from an incoming HTTP request should be extracted.

All **rapidy parameters** are located in the `rapidy.parameters.http` module:

```python
{!> ./docs/docs/server/request/parameters/index/02_parameters_import/01_example.py !}
```

They can also be accessed via the `rapidy.http` module:

```python
{!> ./docs/docs/server/request/parameters/index/02_parameters_import/02_example.py !}
```

## HTTP Request Parameters

You can learn more about each parameter type in the corresponding sections:

- **[Path](../parameters/path)** — *path parameters (used for creating dynamic APIs)*
- **[Headers](../parameters/headers)** — *request header parameters*
- **[Cookies](../parameters/cookies)** — *cookie parameters (automatically extracted from headers)*
- **[Query Parameters](../parameters/query)** — *query parameters passed in the URL*
- **[Body](../parameters/body)** — *request body parameters*

## Data Extraction

Data can be extracted using either the **rapidy parameter**'s `attribute name` or its `alias`.

!!! example "Extraction using attribute name"
    ```python
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/01_name_attr/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/01_name_attr/curl.sh !}
    ```

!!! example "Extraction using alias"
    ```python
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/02_alias/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/request/parameters/index/03_data_extractor/02_alias/curl.sh !}
    ```

## Validation Capabilities

Each **rapidy parameter** inherits from
**<a href="https://docs.pydantic.dev/latest/concepts/fields/" target="_blank">pydantic.Field</a>**
and supports all of its features.

```python
{!> ./docs/docs/server/request/parameters/index/04_validation.py !}
```

## Parameter Annotation Methods

### Defining a Parameter as a Default Value

The simplest and most intuitive way to define a parameter:

```python
{!> ./docs/docs/server/request/parameters/index/05_param_annotation/01_as_default.py !}
```

However, if you use static code analyzers like `mypy`, you might encounter errors:
```
main.py:4: error: Incompatible default for argument "user_id" (default has type "PathParam", argument has type
"int")  [assignment]
```

To prevent this, enable the mypy plugin for **Rapidy**:
```toml
# pyproject.toml
[tool.mypy]
plugins = [
    "pydantic.mypy",
    "rapidy.mypy"     # <-- enable Rapidy plugin
]
```

### Annotation Using `typing.Annotated`

You can read more about `typing.Annotated` in the official Python documentation
**<a href="https://docs.python.org/3/library/typing.html#typing.Annotated" target="_blank">here</a>**.

```python
{!> ./docs/docs/server/request/parameters/index/05_param_annotation/02_annotated.py !}
```

The `Annotated` annotation uses two key arguments:

- <span class="base-color">The first</span> argument **Annotated[<span class="success-color">int</span>, ...]** defines the expected data type
  (in this case, `int`).
- <span class="base-color">The last</span> argument **Annotated[..., <span class="success-color">PathParam()</span>]** must be one of the
  **Rapidy** HTTP parameters (`Header`, `Headers`, `Cookie`, ..., `Body`).
  In this case, the server expects the `Host` header.

!!! note ""
    Since `Annotated` can accept an unlimited number of parameters, **Rapidy**
    explicitly takes only the **first** and **last** arguments for validation.
    Other parameters may be used as metadata for the validation model in `pydantic`,
    if supported, to perform additional type checks.

!!! warning "Missing HTTP Parameters in `Annotated`"
    If `Annotated` does not contain an HTTP parameter, such as `Annotated[str, str]`,
    the attribute will be ignored.

!!! note "Support for Default Values"
    `Header(default=..., default_factory=...)`

    You can read more about default values in the corresponding section of each HTTP parameter.
