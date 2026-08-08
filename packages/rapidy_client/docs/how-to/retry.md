# Configure retries safely

Retries are enabled by `UpstreamConfig.retry`. The default policy makes at
most three attempts for `GET`, `HEAD`, `PUT`, `DELETE`, and `OPTIONS` when a
response has status 429, 502, 503, or 504, or when a retryable connection error
occurs.

```python
from rapidy_client import BackoffConfig, RetryConfig, UpstreamConfig

config = UpstreamConfig(
    base_url="https://inventory.example.com",
    retry=RetryConfig(
        max_attempts=4,
        statuses=frozenset({429, 502, 503, 504}),
        backoff=BackoffConfig(base=0.2, cap=3.0, jitter="full"),
    ),
)
```

`POST` and `PATCH` are not retried by default because the server may already
have applied their side effects. Add a method to `RetryConfig.methods` only
when that operation is idempotent, or use the declarative endpoint-level
idempotency opt-in when defining a client schema.

Disable retries for one call by passing `retry=None`:

```python
response = await client.post("/orders", json=payload, retry=None)
```

## Retry-After and backoff

For retryable responses, a valid `Retry-After` delta or HTTP date replaces the
normal exponential backoff. It is capped by `retry_after_cap` (30 seconds by
default). Past dates and invalid values fall back to the configured backoff.
Full jitter chooses a random duration between zero and the exponential
ceiling, capped by `BackoffConfig.cap`.

Before sleeping, the client closes the unsuccessful response so its connection
can return to the pool. One-shot async request bodies are never replayed.

## Retry budget

The client keeps a token bucket per upstream client. Primary traffic
replenishes it by `budget_ratio`; retries consume tokens. When the bucket is
empty, the client returns or raises the last real outcome and emits a
`budget_exhausted` observer event—it does not replace the outcome with a new
exception. Set `budget_ratio=None` to disable this throttle while retaining
`max_attempts`.

Retry sleeps are also capped by the remaining logical deadline. If the next
attempt no longer has enough budget for its connect phase, it fails before any
network call.
