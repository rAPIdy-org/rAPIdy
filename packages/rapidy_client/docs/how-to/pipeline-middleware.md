# Pipeline middleware

The client builds its middleware onion once. Request-specific behavior travels
through `RequestExtensions`; it does not rebuild or reorder the onion.

## Layer order

The stable outside-in order is:

```text
correlation
→ client middlewares
→ declared middlewares
→ breaker → rate limit → bulkhead
→ retry
→ auth → per-attempt middlewares → trace context
→ deadline → total timeout → redirect
→ transport
```

Some stock slots are intentionally empty until their owning feature is enabled.
An empty slot is a transparent pass-through, so enabling it later preserves the
relative order of every other layer.

Status handling and response parsing are outside the pipeline. A middleware can
therefore inspect and return a 4xx or 5xx `Response` without the transport or
client converting it first.

## Write a user middleware

A middleware receives the request and the next onion layer. It must call the
next layer exactly as many times as its policy intends:

```python
from rapidy_client import CallNext, Request, Response


class ServiceHeaderMiddleware:
    async def __call__(
        self,
        request: Request,
        call_next: CallNext,
    ) -> Response:
        request.headers = type(request.headers)(
            [*request.headers.multi_items(), ("X-Service", "catalog")]
        )
        return await call_next(request)
```

Client middlewares are outside retry and run once per logical call.
`per_attempt_middlewares` are inside retry and may run more than once.

## Per-request extensions

Stock middleware reads effective configuration from `request.extensions` on
every call. Important fields include `timeout`, `retry`, `deadline`, `attempt`,
`request_id`, and `custom`. A layer should read only the fields it owns and must
not rewrite another layer's fields.

Use `extensions.custom` for coordinated application-specific values:

```python
tenant = request.extensions.custom.get("tenant")
```

Because the extension object belongs to the request, two calls through the same
prebuilt pipeline can carry different overrides safely.

## Declarative middleware

Endpoint declarations store their middleware tuple in
`extensions.declared_middlewares`. `DeclaredMiddlewaresSlot` executes that
tuple as-is: controller middleware first, then method middleware. The
declarative writer owns that ordering; the slot neither sorts the tuple nor
rebuilds the client pipeline.

## One-shot request bodies

An `AsyncIterable[bytes]` body is non-replayable. In debug mode, reading or
replacing `request.content` from middleware raises `RuntimeError`, which catches
logging and signing middleware that would accidentally consume a one-shot
upload. The transport still receives the original raw request.

Middleware that needs body access should require replayable `bytes` or a
`ContentFactory`. Outside debug mode the guard is not installed, but the
replayability contract still applies.
