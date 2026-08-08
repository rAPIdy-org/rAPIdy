# Redirects, response limits, and content encoding

Redirect following is disabled by default. Enable it for one upstream or one
call:

```python
from rapidy_client import HttpClient, RedirectConfig, UpstreamConfig

config = UpstreamConfig(
    base_url="https://catalog.example.com",
    redirects=RedirectConfig(follow=True, max_redirects=5),
)
client = HttpClient(config)

response = await client.get("/products", follow_redirects=False)
```

The client follows `301`, `302`, `303`, `307`, and `308` responses that contain
`Location`. A `303` changes every method except `HEAD` to `GET`; `301` and `302`
change `POST` to `GET`; `307` and `308` preserve method and body. Use
`ContentFactory` when a preserved request body must be replayable.

## Redirect security

Cross-origin redirects are blocked while `allow_absolute_urls=False`, the safe
default. Allow them only for a deliberate upstream contract:

```python
config = UpstreamConfig(
    base_url="https://login.example.com",
    allow_absolute_urls=True,
    redirects=RedirectConfig(follow=True),
)
```

When the origin changes, the client removes `Authorization`, `Cookie`,
`Proxy-Authorization`, and `Host`. Secret stripping can be disabled with
`strip_auth_on_origin_change=False`, but that should be reserved for trusted
origins. Exceeding `max_redirects` raises `TooManyRedirectsError`; a blocked
cross-origin hop raises `RedirectNotAllowedError`. Intermediate responses are
closed before the next hop.

## Body limits

`max_response_size` limits decoded bytes buffered by `aread()`, `text()`, and
`json()`. It raises `BodyTooLargeError` before an oversized body is retained.
Streaming through `aiter_bytes()` is deliberately unlimited because the caller
controls consumption.

```python
config = UpstreamConfig(
    base_url="https://catalog.example.com",
    max_response_size=8 * 1024 * 1024,
    error_body_limit=64 * 1024,
)
```

For a buffered request that raises `StatusError`, only `error_body_limit` decoded
bytes are retained in `error.response`. The default is 65536 bytes.

## Content-Encoding

`gzip` and incoming `deflate` are always supported. Install `rapidy-client[brotli]`
for `br`; install `rapidy-client[zstd]` on Python 3.13 for `zstd` (Python 3.14+
uses `compression.zstd`). `Accept-Encoding` advertises only codecs available in
the current runtime. An unsupported encoding raises `DecodeError` with the
required extra in its message.

Decoding is incremental for streamed responses. Version 1 accepts one
`Content-Encoding` value; chained encodings fail explicitly with `DecodeError`.
