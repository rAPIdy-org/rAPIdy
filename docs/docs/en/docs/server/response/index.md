# HTTP-Response
The section describes how to create and send an HTTP response in **`Rapidy`**.

## Description
**HTTP Response** is a message sent by the server to the client in response to their request.

??? example "Example of a text HTTP response (HTTP/1.1 protocol)"
    ```
    {!> ./docs/docs/server/response/01_text_response_example.txt !}
    ```

### Structure of an HTTP response
An HTTP response consists of a status line, headers, and a body.

#### Status Line
`HTTP/1.1 200 OK`

The status line (or status string) includes:

- **Protocol version** *(HTTP protocol)* — <span class="note-color">HTTP/1.1</span>
- **Status code** *(numerical code indicating the status of the request)* — <span class="green-color">200</span>
- **Explanation** *(brief textual description of the status code)* — OK

??? info "HTTP Protocol Versions"
    HTTP standards are developed by the Internet Engineering Task Force (IETF) and the World Wide Web Consortium (W3C), resulting in a series of documents called Requests for Comments (RFC).

    | Protocol Version | HTTP Protocol Type | Transport Layer  | Description                                                                                      |
    | ---------------- | ------------------ | ---------------- | ------------------------------------------------------------------------------------------------ |
    | HTTP/1.1         | Textual            | TCP              | Requires waiting for a response before sending the next request on the same connection.          |
    | HTTP/2           | Binary             | TCP              | Allows sending multiple requests simultaneously without waiting for the previous ones to finish. |
    | HTTP/3/QUIC      | Binary             | UDP              | Operates over UDP (uses QUIC technology).                                                        |

??? info "HTTP Status Codes"
    HTTP status codes inform the client of the result of processing their request. They are divided into five categories:

    | Code    | Description                                                        |
    | ------- | ------------------------------------------------------------------ |
    | **1xx** | Informational codes, not affecting the request processing.         |
    | **2xx** | Successful request processing.                                     |
    | **3xx** | Redirection to another resource.                                   |
    | **4xx** | Client-side errors (e.g., invalid request or lack of permissions). |
    | **5xx** | Server-side errors.                                                |

#### Response Headers
Response headers (Response Headers) specify details about the response but do not affect the content of the body.

??? example "Examples of headers"
    | Category  | Example                        | Description                                             |
    |-----------|---------------------------------|------------------------------------------------------- |
    | Server    | Server: nginx                   | Information about the server that handled the request. |
    | Set-Cookie| Set-Cookie:UserData=SomeData123 | A cookie with user information stored by the browser.  |

#### Response Body
An optional part of the response containing data.

The server specifies the type of transmitted data using the `Content-Type` header.

The response body can represent JSON, a media file, a document, text, or even an arbitrary set of bytes.

## Generating an HTTP Response
A simple HTTP handler response might look like this:
```python
{!> ./docs/docs/server/response/02_simple_response_example.py !}
```

### Validation and Serialization of the Response
`Rapidy` uses `pydantic` for validation and serialization of responses.

!!! info "When the server starts, `Rapidy` creates a `pydantic` model for each handler based on the return annotation and uses it to validate data in the response."

!!! tip "You can override the type for validation or cancel the creation of the `pydantic` model using the `response_validate` and `response_type` attributes."
    ```python hl_lines="5"
    {!> ./docs/docs/server/response/handler_response/response_validate.py !}
    ```

    !!! info "More about response attributes for HTTP handlers can be read [here](handler_response)."

??? example "Examples of successful responses"
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/01_success/01_example.py !}
    ```
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/01_success/02_example.py !}
    ```
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/01_success/03_example.py !}
    ```

??? example "Examples of failed responses"
    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/01_example/example.py !}
    ```
    ```text
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/01_example/response.txt !}
    ```

    ```python
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/02_example/example.py !}
    ```
    ```text
    {!> ./docs/docs/server/response/11_validation_and_serialization/02_failed/02_example/response.txt !}
    ```

### Advanced HTTP Response Management
`Rapidy` uses the `Response` object for managing HTTP responses.
```python
{!> ./docs/docs/server/response/03_response_import.py !}
```

The `Response` object can be created either by `Rapidy` internally to form a response or by the developer for explicit control.

!!! info "More about the `Response` object can be read [here](response_object)."

#### Automatic Creation of Response Object
`Rapidy` automatically creates a `Response` in the following cases:

**If a handler defines an attribute with any name and type `Response`**
```python
{!> ./docs/docs/server/response/04_response_inject.py !}
```

This gives the developer more flexibility in managing HTTP responses, allowing, for example, setting status codes, cookies, and other parameters.
Learn more about the `Response` object attributes [here](response_object/#_1).

```python hl_lines="5 9 12"
{!> ./docs/docs/server/response/05_response_inject_ext.py !}
```

You can also return the same `Response` object.
```python hl_lines="5"
{!> ./docs/docs/server/response/06_return_injected_response.py !}
```

**The handler returns a `python` object**
```python hl_lines="5"
{!> ./docs/docs/server/response/02_simple_response_example.py !}
```

!!! info "If a handler already has an attribute with type `Response`, and the handler returns a `python` object, a new instance of `Response` will not be created."
    ```python hl_lines="5"
    {!> ./docs/docs/server/response/07_injected_response_not_recreated.py !}
    ```

#### The handler returns a Response object
`Rapidy` allows the developer to manage and create the `Response` object manually.

```python
{!> ./docs/docs/server/response/13_new_response_obj.py !}
```

!!! warning "When directly managing the response, handler attributes are ignored."

    ```python
    {!> ./docs/docs/server/response/08_ignore_content_type.py !}
    ```

!!! warning "If the `Response` object was injected as an attribute, and the developer returns a new `Response`, the injected `Response` is ignored."

    ```python hl_lines="9"
    {!> ./docs/docs/server/response/09_ignore_injected_response.py !}
    ```

!!! note "When directly managing the response, `pydantic` validation will not work."

    ```python hl_lines="5"
    {!> ./docs/docs/server/response/10_response_obj_pydantic.py !}
    ```

#### The handler returns None
If the `Rapidy` handler returns nothing, `Rapidy` will return the current `Response` object by default.

!!! warning "If you modified the request and returned nothing from the handler, this modified request will be returned!"

```python
{!> ./docs/docs/server/response/12_none_return.py !}
```

#### HTTP Handler Attributes
The response attributes of a web handler are used to manage the formation of the response when returning any `python` object from the handler.

##### Default Status Code
To manage the default status code, you can define the `status_code` attribute.

```python hl_lines="6 13"
{!> ./docs/docs/server/response/handler_response/status_code.py !}
```

!!! info "You can read about other attributes [here](handler_response)."

!!! tip "Rapidy allows you to manage attributes across all handler types, including those styled like aiohttp."
    ```python hl_lines="12 13"
    {!> ./docs/docs/server/response/handler_response/aiohttp_style_example.py !}
    ```
