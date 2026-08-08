# Observability, correlation, and DI ownership

`HttpClient` emits lifecycle events through async observers. Implement
`BaseObserver` and override only the hooks you need:

```python
from rapidy_client.observability import BaseObserver, RequestContext


class MetricsObserver(BaseObserver):
    async def on_request_end(self, ctx, response):
        record_latency(ctx.upstream, ctx.endpoint, ctx.elapsed, response.status)
```

Pass observers when constructing a client. Observer failures are logged and do
not change the request result; task cancellation is always propagated.
`on_request_end` receives every returned response, including 4xx and 5xx,
before `raise_for_status` can create `StatusError`. Transport-backed clients
also emit `on_pool_wait` and `on_connection_open`.

## Built-in request logging

`LoggingObserver` is enabled by default through `UpstreamConfig.log` and writes
one JSON event to the `rapidy_client.http` logger. Levels control fields, not
Python log severity:

- `off`: no built-in logging observer;
- `meta`: method, endpoint template, status, duration, attempt, request ID;
- `headers`: metadata plus redacted request/response headers;
- `body`: headers plus available buffered body previews.

```python
from rapidy_client import LogConfig, UpstreamConfig

config = UpstreamConfig(
    base_url="https://catalog.example.com",
    log=LogConfig(
        level="headers",
        redact_headers_extra=frozenset({"x-tenant-token"}),
        redact_query_extra=frozenset({"session"}),
    ),
)
```

Authorization, proxy authorization, cookies, API keys, and deny-listed query
values are redacted before model reprs, exception text, or framework logs are
produced. Body previews are cropped to `max_body_len`. Arbitrary application
model reprs are outside this guarantee; use `pydantic.SecretStr` or
`Field(repr=False)` for secret DTO fields.

## Correlation IDs

Set `rapidy_client_request_id` in the current context. The built-in outer
middleware writes that exact value as a single `X-Request-ID` header, replacing
any caller-provided value:

```python
from rapidy_client.config import rapidy_client_request_id

token = rapidy_client_request_id.set("request-42")
try:
    await client.get("/products")
finally:
    rapidy_client_request_id.reset(token)
```

## Dishka APP-scope ownership

`provide_upstream()` is the client-owned DI lifecycle primitive. It imports DI
types only from `rapidy_core.di`, creates the session lazily on first I/O, and
closes the client when the APP scope exits:

```python
from rapidy_client.di import provide_upstream

catalog_provider = provide_upstream("catalog", config)
```

Resolve `HttpClient` with the same component key. The APP scope owns exactly
one client instance per provider; controller and endpoint bindings are added by
the declarative DI milestone.
