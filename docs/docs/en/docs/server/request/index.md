# Request
The section describes the structure of HTTP requests and methods for handling them in **`Rapidy`**.

## Description
A **web request** is a request sent by a client, such as a web browser, to a server to retrieve a web page or another resource.

### HTTP Request Structure
An HTTP request consists of a start line, headers, and a body.

#### Start Line
Example:
`GET /index.html HTTP/1.1`

The HTTP request start line includes:

- **HTTP request method** (*method*, sometimes referred to as *verb*) — a short word that defines the action to be performed on the requested resource.
- **Request target** — the resource URL, consisting of the protocol, domain name (or IP address), path to the resource on the server, and optionally, the port, HTTP request parameters, and other optional elements.
- **Protocol version** *(HTTP protocol)* — <span class="note-color">HTTP/1.1</span>.

??? info "HTTP Request Methods"

    | Method   | Description                                                                         |
    | -------- | ---------------------------------------------------------------------------------- |
    | GET      | Requests information.                                                             |
    | HEAD     | Requests only headers.                                                            |
    | POST     | Sends data (e.g., login form, text, PDF documents, binary data).                  |
    | PUT      | Creates a new resource.                                                           |
    | PATCH    | Partially updates a resource.                                                     |
    | DELETE   | Deletes a resource.                                                               |
    | OPTIONS  | Requests information about the server (e.g., supported HTTP methods for a resource). |

??? info "HTTP Protocol Versions"
    HTTP standards are developed by the Internet Engineering Task Force (IETF) and the World Wide Web Consortium (W3C), leading to the publication of a series of Requests for Comments (RFC).

    | Version  | Protocol Type | Transport Layer | Description                                                                               |
    | -------- | ------------- | --------------- | ----------------------------------------------------------------------------------------- |
    | HTTP/1.1 | Text-based    | TCP             | Requires waiting for a response before sending the next request within the same connection. |
    | HTTP/2   | Binary        | TCP             | Allows multiplexing, meaning multiple requests can be processed concurrently.              |
    | HTTP/3   | Binary        | UDP (QUIC)      | Operates over UDP, providing faster and more reliable data transmission.                   |

#### Request Headers
An HTTP header is a line formatted as `Header-Name: Value`, where a colon (`:`) serves as a separator.
Header names are case-insensitive: `Host` and `host` are treated the same.
By convention, each word in a header name starts with a capital letter.

??? example "Header Examples"

    | Category     | Description                                                                     |
    |-------------|-------------------------------------------------------------------------------|
    | Host        | Specifies the host from which the resource is requested (can be a domain name or IP address). |
    | User-Agent  | Contains information about the client (browser, version, user's OS).          |
    | Referer     | Indicates the origin of the current request.                                  |
    | Cookie      | Transfers user cookies.                                                       |
    | Content-Type | Specifies the type of data being transmitted in the request body.            |
    | Authorization | Provides credentials for authenticating the client on the server.           |

#### Request Body
The request body is optional and contains data related to the request.
The type of transmitted information is specified in the `Content-Type` header.
The request body can be a JSON object, media file, document, text, byte sequence, etc.

## Managing HTTP Requests
To handle HTTP requests, `Rapidy` uses the `Request` entity.

??? note "More about the `Request` object"
    `Rapidy` is based on `aiohttp` mechanisms and uses `aiohttp.web.Request`.
    In fact, `rapidy.http.Request` is a reference to `aiohttp.web.Request` for ease of use.

    More details on `aiohttp.web.Request` can be found **[here](https://docs.aiohttp.org/en/stable/web_reference.html)**.

This section explains how to extract and validate data from an incoming HTTP request using **`Rapidy`**.

### Retrieving Data via Request Parameters
You can extract and validate any HTTP request parameter using `pydantic` and `Rapidy`'s functionality.

!!! info "Extract a parameter from `rapidy.http`, `rapidy.parameters.http`, or `rapidy.web` (`aiohttp` style)."
    ```python
    {!> ./docs/docs/server/request/01_import/01_example.py !}
    ```

    ??? example "Import from `rapidy.parameters.http`."
        ```python
        {!> ./docs/docs/server/request/01_import/02_example.py !}
        ```

    ??? example "Import from `rapidy.web` (_`aiohttp` style_)."
        ```python
        {!> ./docs/docs/server/request/01_import/03_example.py !}
        ```

!!! tip "For more details, see the **[Parameters](parameters.md)** section."

### Retrieving Data via the Request Object
You can also retrieve data directly from the `rapidy.http.Request` object by adding it as an argument to your HTTP handler.

```python hl_lines="5"
{!> ./docs/docs/server/request/02_get_params_from_request_obj.py !}
```

!!! note "If the handler argument has a `Request` type annotation, its order does not matter."
    ```python hl_lines="7"
    {!> ./docs/docs/server/request/03_inject_request/01_example.py !}
    ```

!!! warning "If the first argument of the handler does not have a type annotation, `Rapidy` will automatically assume `Request`."
    ```python hl_lines="5"
    {!> ./docs/docs/server/request/03_inject_request/02_example.py !}
    ```

!!! note "`Rapidy` utilizes built-in `aiohttp` data extraction mechanisms."
    More details on `aiohttp.web.Request` and its data extraction methods can be found **[here](https://docs.aiohttp.org/en/stable/web_reference.html)**.
