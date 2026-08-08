# Timeouts

`Timeout` separates the limits for each part of an HTTP attempt:

| Field | Default | Covers |
| --- | ---: | --- |
| `connect` | 3 s | TCP and TLS connection establishment |
| `read` | 10 s | waiting for response data |
| `write` | 30 s | sending request data |
| `pool` | 5 s | waiting for an available per-host/pool slot |
| `total` | 10 s | the outer budget for the complete attempt |

Connect, read, write, and pool limits are passed to the native transport for
each request. `total` is deliberately not passed to `httpx2`: the client
attempt layer applies it around the complete operation so that one budget can
cover pool acquisition, connection setup, request upload, response download,
and middleware work.

The foundation-level per-request override lives on `RequestExtensions`:

```python
from rapidy_client import Timeout

timeout = Timeout(
    total=20.0,
    connect=1.0,
    read=15.0,
    write=5.0,
    pool=0.5,
)
```

Use a short `connect` limit when an upstream must fail fast, a larger `read`
limit for slow responses, and a bounded `pool` limit to avoid hidden queueing
under load. Increase `write` for large or deliberately throttled uploads.

Every timeout crossing the public boundary is a `HttpTimeoutError`. Inspect its
`phase` value (`connect`, `read`, `write`, `pool`, or `total`) for metrics and
policy decisions instead of parsing the exception message. The original native
exception remains available through `__cause__`.
