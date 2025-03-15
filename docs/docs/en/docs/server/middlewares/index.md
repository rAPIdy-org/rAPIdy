# Middlewares

## Description

`Middleware` is an intermediate software layer that allows performing specific actions before and after processing a request by a route.

```python
{!> ./docs/docs/server/middlewares/01_simple_middleware.py !}
```

!!! note "Attribute Order"
    In a web handler, the first argument is always `Request`, and the second is `CallNext` (_the request handler or `middleware` in the chain_).
    *(They have the same signature — `rapidy.typedefs.CallNext`.)*

!!! note "Handler Response Type"
    The response from a web handler or the next `middleware` in the chain will always be `StreamResponse`. Keep this in mind when designing your `middleware`.

---

## Creation Methods

There are two ways to create `middleware`.

### Without Parameters

This approach is suitable if you do not need to manage the request within the `middleware`.

```python
{!> ./docs/docs/server/middlewares/02_create_without_parameters.py !}
```

### With Parameters

Use this approach if you want more flexibility in managing the response to a request.

```python
{!> ./docs/docs/server/middlewares/03_create_with_parameters.py !}
```

---

## Attributes

`Rapidy-middleware` supports all data validation mechanisms available in web handlers, as well as response handling.

### Validation

Like web handlers, `middleware` can access request objects via attributes.

!!! tip "Before proceeding, we recommend reviewing the section [Request — Managing HTTP Requests](../request) since `middleware` follows the same logic for handling request parameters."

!!! example "Processing a `Bearer` token."
    ```python
    {!> ./docs/docs/server/middlewares/04_validate.py !}
    ```

!!! info "If you extract the `body` both in `middleware` and in the handler, you will not encounter an error about data being read multiple times."
    Extracted data is cached in memory and reused during validation.

---

### Response Management

Like web handlers, `middleware` can manage responses using its own attributes.

!!! tip "Before proceeding, we recommend reviewing the section [Response — Managing HTTP Responses](../response) since `middleware` follows the same response handling logic."

!!! note "Response management is only possible if the `middleware` returns an unprocessed data type *(anything other than `Response` or `StreamResponse`).*"

    ??? example "`Middleware` manages the response using attributes."

        ```python hl_lines="11 15"
        {!> ./docs/docs/server/middlewares/05_response/01_response_management.py !}
        ```

    ??? example "`Middleware` cannot manage the response using attributes."

        ```python hl_lines="11 15"
        {!> ./docs/docs/server/middlewares/05_response/02_response_management.py !}
        ```

!!! info "Accessing `Response`."
    ```python hl_lines="5"
    {!> ./docs/docs/server/middlewares/05_response/03_response_inject.py !}
    ```
    !!! warning "`Response` is created only for the current `middleware`."

#### `Middleware` Returns a Different Data Type

If `middleware` returns any data type other than `StreamResponse`, specify this type in `Union` so that `Rapidy` can use it for response validation.

```python hl_lines="5"
{!> ./docs/docs/server/middlewares/05_response/04_response_diff_types.py !}
```
