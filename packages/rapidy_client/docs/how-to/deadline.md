# Bound work with deadlines and total timeouts

A deadline is a logical budget shared by retries. Pass its duration in seconds
to a call:

```python
response = await client.get("/inventory/42", deadline=5.0)
```

The client converts that duration to an absolute monotonic deadline. Before
each attempt it recomputes the remainder, caps `Timeout.total`, and replaces
the propagated `x-rapidy-deadline-ms` header with the current number of
milliseconds.

If the remaining budget is smaller than the effective connect timeout, the
client raises `DeadlineExceededError` without calling the transport. Retry and
`Retry-After` sleeps are capped by the same remainder.

## Propagate an incoming budget

Use the context variable when an inbound request budget should flow to an
upstream call:

```python
from rapidy_client.config import rapidy_client_deadline

token = rapidy_client_deadline.set(5.0)
try:
    await client.get("/catalog")
finally:
    rapidy_client_deadline.reset(token)
```

The context value is a duration in seconds. `DeadlineConfig.respect_incoming`
controls whether it is used, while `propagate` controls the outgoing header:

```python
from rapidy_client import DeadlineConfig, UpstreamConfig

config = UpstreamConfig(
    base_url="https://catalog.example.com",
    deadline=DeadlineConfig(
        respect_incoming=True,
        propagate=True,
        header="x-rapidy-deadline-ms",
    ),
)
```

## Deadline versus `Timeout.total`

`Timeout.total` is a wall around one attempt, including all redirect hops in
that attempt. A logical deadline spans retry attempts and their backoff sleeps.
When both are present, the smaller remaining value wins. A total wall expiry
raises `HttpTimeoutError` with `phase="total"`; it is not retried because the
request body may already have reached the server.

For streaming calls, total timeout may be disabled with `total=None`. Supplying
a logical deadline still caps an individual attempt to the current remainder.
