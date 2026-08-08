# HTTP client

`HttpClient` binds one upstream configuration to one connection pool and one
immutable middleware pipeline.

```python
from rapidy_client import HttpClient, UpstreamConfig

config = UpstreamConfig(base_url="https://catalog.example.com")

async with HttpClient.simple(str(config.base_url)) as client:
    response = await client.get("/products/{id}", path_params={"id": 42})
    payload = await response.json()
```

Use `simple()` for a short-lived client with configuration overrides. For a
long-lived service client, construct `HttpClient(config)` once, reuse it, and
call `await client.aclose()` during application shutdown.

## Request bodies and parameters

`request()` and the `get`, `post`, `put`, `patch`, `delete`, `head`, and
`options` shortcuts support escaped path parameters, repeated query values,
headers, JSON, raw/streamed content, and form data.

```python
response = await client.post(
    "/search/{scope}",
    path_params={"scope": "new/items"},
    query={"tag": ["python", "async"], "available": True},
    json={"limit": 20},
)
```

Only one of `json`, `content`, `data`, or `files` may be supplied. Multipart
`files` support is introduced with the streaming/files feature.

Absolute request URLs are rejected by default, which keeps an upstream client
from becoming an accidental SSRF proxy. Set `allow_absolute_urls=True` only for
a deliberate use case.

## Per-call overrides

Configuration is resolved from weaker to stronger levels:

```text
library defaults → UpstreamConfig → declaration → call arguments
```

For `timeout`, a `Timeout` object replaces all phases. A float changes only
`total`, preserving connect/read/write/pool values. `None` disables only the
total limit, and `UNSET` skips the level.

```python
response = await client.get(
    "/report",
    timeout=2.5,
    retry=None,
    follow_redirects=True,
    raise_for_status=False,
)
```

The same prebuilt pipeline can handle different overrides because effective
values are stored in each request's `RequestExtensions`.

## Status and streaming

Buffered requests read the body before returning. By default, 4xx and 5xx
responses raise `StatusError` after the middleware pipeline has completed;
middleware can always inspect the original response. Pass
`raise_for_status=False` to return error responses unchanged.

Use the streaming context to keep body consumption lazy and guarantee cleanup:

```python
async with client.stream("GET", "/export") as response:
    async for chunk in response.aiter_bytes():
        consume(chunk)
```

A stream has no total timeout by default, while its phase timeouts remain
active. Open finite streams drain during shutdown; future WS/SSE sessions are
closed immediately. New work is rejected once shutdown starts.

If a transport is passed explicitly, the caller owns it. A client-created
transport is closed by `HttpClient.aclose()`. A client also binds to the event
loop of its first request and raises `RuntimeError` if reused from another loop.
