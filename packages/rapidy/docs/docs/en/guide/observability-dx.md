# Observability and developer experience

## Structured access logs

`AccessLogMiddleware` wraps the final ASGI application and emits one `AccessLogRecord` when the response or
WebSocket exchange finishes:

```python
from rapidy import Rapidy
from rapidy.observability import AccessLogMiddleware

rapidy_app = Rapidy(http_route_handlers=routes)
app = AccessLogMiddleware(rapidy_app)
```

Records contain protocol, method, matched route template, status, latency, request/response byte counts, request ID,
trace ID, and WebSocket close code. They never contain the concrete request path, query string, headers, credentials,
or path-parameter values. Unmatched requests share the stable `{unmatched}` label. Use `JSONAccessFormatter` from
`rapidy.observability` for compact JSON logs or pass a synchronous `emit` callback to enqueue records.

Place `RequestIDMiddleware` inside the application to populate `request_id`. A valid W3C `traceparent` is reduced to
its trace ID; the complete header is never retained in the record.

## OpenTelemetry

OpenTelemetry remains optional:

```bash
pip install "rapidy[otel]"
```

```python
from rapidy.observability import instrument_app

app = instrument_app(rapidy_app, tracer_provider=tracer_provider, meter_provider=meter_provider)
```

The wrapper uses the official OpenTelemetry ASGI middleware for HTTP and WebSocket spans and metrics. Span names and
`http.route` attributes use registered templates such as `GET /users/{user_id}`. Server request/response header
capture is disabled by default. Exporters and providers remain application-owned.

## Problem Details and exception handlers

Exception handlers are application-local and inherit through mounts. The most specific handler on the deepest
mounted application wins:

```python
from rapidy import Rapidy
from rapidy.exceptions import HTTPException
from rapidy.problems import ProblemDetailsRenderer

app = Rapidy(
    exception_handlers={
        HTTPException: ProblemDetailsRenderer(type_base_url='https://api.example.com/problems'),
        DomainError: ProblemDetailsRenderer(),
    },
)
```

`ProblemDetailsRenderer` produces RFC 9457 `application/problem+json`. Unexpected exception details are hidden by
default. If a response has already started, handlers are not called and rAPIdy only finalizes the existing stream.
Custom handlers may be synchronous or asynchronous and must return `Response` or `StreamResponse`.

## Named routes and reverse URLs

```python
@get('/users/{user_id:\\d+}', name='user.detail')
async def user(user_id: int = PathParam()): ...

app.url_for('user.detail', user_id=42)       # /users/42
request.url_for('user.detail', user_id=42)   # includes ASGI root_path
```

Reverse lookup raises typed errors for missing, unexpected, invalid, unknown, or ambiguous parameters. A named
`StaticFiles('/assets', name='assets', ...)` tree supports `app.static_url('assets', 'js/app.js')`; its root route is
named `assets:index`.

## CLI and conventional docs paths

```bash
rapidy dev main:app --reload
rapidy run main:app --host 0.0.0.0 --port 8080
rapidy routes main:rapidy_app
rapidy check main:rapidy_app
```

`routes --json` is suitable for tooling. `check` reports route, name, mount, and OpenAPI configuration without dumping
application state or environment values. The legacy `python -m rapidy main:app` form continues to mean `run`.

OpenAPI stays opt-in. Use `OpenAPIConfig.docs(...)` when the conventional paths are preferred:

```python
app = Rapidy(openapi_config=OpenAPIConfig.docs(title='Users API', version='1'))
```

This serves `/openapi.json`, `/docs`, and `/redoc`.
