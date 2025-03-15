# HTTP errors

## Description

**HTTP errors** are objects with specific logic that can return a web server response with a predefined `HTTP code`.

!!! info "Errors are raised using the `raise` statement."

```python hl_lines="6"
{!> ./docs/docs/server/http_errors/01_handler_raise_400/example.py !}
```

**HTTP errors** can be raised either by the developer or by the `Rapidy` web server itself if a client or server makes a mistake.

!!! info "All errors are located in the `rapidy.web_exceptions` module, but they can also be imported from `rapidy.http`."

## Types of HTTP errors

`Rapidy` supports four types of **HTTP errors**:

- **2xx** — successful responses *(base class — `HTTPSuccessful`)*
- **3xx** — redirections *(base class — `HTTPRedirection`)*
- **4xx** — client errors *(base class — `HTTPClientError`)*
- **5xx** — server errors *(base class — `HTTPServerError`)*

!!! tip "Base classes can be used to handle all child errors."
!!! info "More details about **HTTP errors** can be found in the `aiohttp` documentation **<a href='https://docs.aiohttp.org/en/stable/_modules/aiohttp/web_exceptions.html' target='_blank'>here</a>**."

## Raising HTTP errors

### Raising an HTTP error by the developer

A developer can manually raise an error if request processing follows an unsuccessful scenario.

```python hl_lines="6"
{!> ./docs/docs/server/http_errors/01_handler_raise_400/example.py !}
```

```bash
{!> ./docs/docs/server/http_errors/01_handler_raise_400/curl.sh !}
```

```text
{!> ./docs/docs/server/http_errors/01_handler_raise_400/curl__response.txt !}
```

### Raising an HTTP error by the web server

The web server will automatically raise an error if a request cannot be processed.

??? example "Not Found — `404`"
    ```python
    {!> ./docs/docs/server/http_errors/02_handler_not_found/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/http_errors/02_handler_not_found/curl.sh !}
    ```
    ```text
    {!> ./docs/docs/server/http_errors/02_handler_not_found/curl__response.txt !}
    ```

??? example "Method Not Allowed — `405`"
    ```python
    {!> ./docs/docs/server/http_errors/03_method_not_allowed/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/http_errors/03_method_not_allowed/curl.sh !}
    ```
    ```text
    {!> ./docs/docs/server/http_errors/03_method_not_allowed/curl__response.txt !}
    ```

#### Validation Error

If a web request fails validation, the client will receive a response in `application/json` format with an error description.

```python
{!> ./docs/docs/server/http_errors/04_request_validation_failure/example.py !}
```
```bash
{!> ./docs/docs/server/http_errors/04_request_validation_failure/curl.sh !}
```
```text
{!> ./docs/docs/server/http_errors/04_request_validation_failure/curl__response.txt !}
```

!!! info "The `HTTPValidationFailure` error contains a list of errors in the `validation_errors` field."

    To access these errors, you can catch `HTTPValidationFailure`:
    ```python
    {!> ./docs/docs/server/http_errors/05_catch_422/01_example.py !}
    ```

!!! info "`HTTPValidationFailure` inherits from `HTTPUnprocessableEntity`."

    This means that both errors can be handled using `HTTPUnprocessableEntity` if you do not need to disclose detailed error information to the client.
    ```python
    {!> ./docs/docs/server/http_errors/05_catch_422/02_example.py !}
    ```

## Error Handling

Sometimes it is necessary to catch an error, for example, to modify the server response.

This can be done using `middleware`:

```python
{!> ./docs/docs/server/http_errors/06_catch_422_middleware.py !}
```

??? example "Example of handling all errors with a unified response"

    ```python
    {!> ./docs/docs/server/http_errors/07_catch_422_middleware_full.py !}
    ```
