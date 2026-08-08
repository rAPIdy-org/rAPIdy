# HTTP transport

`HttpxTransport` is the HTTP/1.1 and HTTP/2 transport adapter for
`rapidy-client`. It owns the `httpx2`/`httpcore2` integration; the rest of the
package depends only on rAPIdy's `Request`, `Response`, and `BaseTransport`
contracts.

## Connection pool

The transport accepts the pool, TLS, and optional proxy value objects from the
client configuration layer. Pool settings control:

- `max_connections`: the global native connection-pool limit;
- `max_per_host`: the rAPIdy per-host concurrency limit;
- `keepalive_timeout`: how long an idle connection remains reusable;
- `force_close`: disables keep-alive when true.

The per-host slot remains occupied until the response body is consumed or the
response is explicitly closed. Always use `await response.aread()`, iterate the
body to completion, or call `await response.aclose()`.

`Response.extensions` reports elapsed transport time, attempt number, pool wait
time, and whether the native connection was reused when that information is
available.

## Protocol and policy boundaries

Redirect following is disabled in the transport. It also returns 4xx and 5xx
responses unchanged and never converts status codes into exceptions. Redirect,
retry, and status policies belong to higher client layers.

HTTP/2 is enabled when the optional dependency is installed:

```shell
pip install "rapidy-client[http2]"
```

Without the extra, the same transport uses HTTP/1.1. TLS verification is on by
default in the configuration layer; custom CA files, TLS 1.2/1.3 minimums,
client certificates, and an explicit proxy are passed to the native client.
Cookie persistence is opt-in through the `shared` policy; the default
`disabled` policy does not retain `Set-Cookie` values between requests.

## Stable transport errors

Native exceptions do not leak through the public transport boundary:

| Failure | rAPIdy error |
| --- | --- |
| DNS lookup | `DNSResolveError` |
| TLS handshake or certificate | `TLSError` |
| proxy connection | `ProxyError` |
| other connection failure | `ConnectError` |
| server disconnect before a response | `ServerDisconnectedError` |
| malformed or incomplete protocol data | `ProtocolError` |
| connect/read/write/pool/total timeout | `HttpTimeoutError` with `phase` |
| response decoding | `DecodeError` |
| other I/O failure | `TransportError` |
| invalid URL or unsupported scheme | `ValueError` |

Mapped errors retain the native exception in `__cause__` and carry the safe
request context (`upstream`, `endpoint`, and `request_id`).
