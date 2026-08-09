# Middleware and mounts

Middleware forms an onion in registration order: the first middleware is outermost. It receives `Request` and
`call_next`, may validate the same HTTP sources as a handler, may short-circuit, and may modify the returned response.

```python
from rapidy import Rapidy
from rapidy.http import get, Header, HTTPRouter, PathParam, Request, Response
from rapidy.middlewares import middleware
from rapidy.typedefs import CallNext


@middleware(response_exclude_none=True)
async def require_token(
    request: Request,
    call_next: CallNext,
    token: str = Header(alias='X-Token'),
) -> Response:
    request.state.token = token
    response = await call_next(request)
    response.headers['X-Authenticated'] = 'true'
    return response


@get('/items/{item_id}')
async def item(request: Request, item_id: str = PathParam()) -> dict[str, str]:
    return {'item': item_id, 'token': request.state.token}


api = HTTPRouter('/api', [item])
app = Rapidy(middlewares=[require_token], http_route_handlers=[api])
```

See the executable
[`examples/middleware_mounts.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/middleware_mounts.py).

## Middleware responses

Decorated middleware accepts the handler `response_*` options, including validation, aliases, include/exclude,
`response_exclude_none`, content type, status, headers, cookies, and JSON encoder. Plain async middleware is also
accepted when it already returns `Response`.

Exceptions raised inside the onion reach outer middleware. A framework `HTTPException` that escapes the onion is
rendered once by the application; an unknown exception becomes a logged plain-text HTTP 500.

## Production middleware

The built-in production stack is configured with callable middleware objects. Registration order is request order;
the first item is the outermost. Put proxy normalization before every policy that consumes the scheme or host:

```python
from rapidy import Rapidy
from rapidy.middlewares import (
    CompressionMiddleware,
    CORSMiddleware,
    HTTPSRedirectMiddleware,
    ProxyHeadersMiddleware,
    RequestIDMiddleware,
    TrustedHostMiddleware,
)


app = Rapidy(
    middlewares=[
        ProxyHeadersMiddleware(['10.0.0.0/8', '192.0.2.10']),
        TrustedHostMiddleware(['api.example.com', '*.internal.example.com']),
        HTTPSRedirectMiddleware(['api.example.com', '*.internal.example.com']),
        RequestIDMiddleware(),
        CORSMiddleware(
            allow_origins=['https://console.example.com'],
            allow_methods=['GET', 'POST'],
            allow_headers=['authorization', 'content-type'],
            allow_credentials=True,
            allow_private_network=False,
        ),
        CompressionMiddleware(algorithms=['br', 'gzip'], minimum_size=500),
    ],
)
```

`ProxyHeadersMiddleware` accepts standardized `Forwarded` and `X-Forwarded-*` metadata only when the immediate ASGI
peer belongs to `trusted_proxies`. It walks the address chain from the trusted edge towards the first untrusted hop.
Never list a broad network unless every proxy in it overwrites or sanitizes forwarding fields.
The built-in Uvicorn launcher disables Uvicorn's separate proxy-header rewriting by default, so this middleware owns
the trust boundary. Passing `proxy_headers=True` to `run_app()` is an explicit alternative and should not be combined
with an independently configured trust policy by accident.

`TrustedHostMiddleware` accepts exact names and leading `*.` subdomain patterns, rejects missing/duplicate/invalid
`Host`, and can redirect the bare name to an allowed `www.` name. `HTTPSRedirectMiddleware` requires its own exact or
leading-wildcard host allowlist, preserves the raw path and query, and uses 307 by default. This prevents an
attacker-controlled `Host` from becoming an off-site redirect even if the middleware is accidentally used without
`TrustedHostMiddleware`. It must run after trusted proxy normalization when TLS terminates at the edge.

`RequestIDMiddleware` accepts one safe `X-Request-ID` or generates a UUID, stores `request_id` and
`request_context` in `request.state`, adds the response field on success and framework errors, and exposes
`get_request_id()` / `get_request_context()` through an isolated `ContextVar`. The context remains available while a
streaming iterable is consumed.

`CORSMiddleware` supports simple responses, preflight, regex origins, exposed fields, max age, and the Private Network
Access opt-in. Credentialed CORS rejects wildcard origins, request headers, and exposed headers at startup. A PNA
preflight is denied unless `allow_private_network=True` is explicit.

`CompressionMiddleware` negotiates quality-weighted Brotli/gzip, updates `Vary: Accept-Encoding` and
`Content-Length`, weakens a strong ETag, and removes obsolete content digests. It does not transform HEAD, Range/206,
SSE, `no-transform`, binary media, or an already encoded response. `minimum_size` applies to buffered responses;
eligible streams are compressed incrementally. Imperative `prepare`/`write` streams keep CORS and request-ID fields
but are not compressed because their body has already entered the transport.

Gzip uses only the standard library. Install `rapidy[brotli]` to configure `algorithms=['br', 'gzip']`.
`GZipMiddleware` is the gzip-only convenience class. The compatibility `response_zlib_executor` and
`response_zlib_executor_size` options now control buffered compression execution when compression middleware is
active; they still do not enable compression by themselves.

The complete executable configuration is
[`examples/production_middlewares.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/production_middlewares.py).

## `HTTPRouter` and mounts

Application middleware wraps HTTP dispatch only. WebSocket handshakes use security requirements, guards, and
`WebSocketSecurityConfig`; CORS and `TrustedHostMiddleware` must not be assumed to protect WebSockets.

`HTTPRouter(prefix, handlers, ...)` creates a nested application. Routers can be nested recursively and have their own
middleware, `client_max_size`, `multipart_limits`, startup/shutdown/cleanup hooks, and lifespan contexts. Matching uses
the longest mount prefix. The request's `app` is rebound while the child handles it, while DI remains rooted in the
parent container.

Routes are frozen at startup. Register handlers and mounts before the lifespan begins.

### Custom route regular expressions

`{name}` uses the built-in segment matcher. A template such as `{item_id:\d+}` embeds a Python regular expression
and is evaluated synchronously in the event loop for every candidate route. rAPIdy validates template structure and
compiles the expression at registration, but Python's `re` engine does not provide a match timeout or a linear-time
guarantee. Compilation success therefore does not mean that an expression is resistant to catastrophic
backtracking.

Treat custom route expressions as trusted application source: never construct them from requests, tenant data, or
unreviewed runtime configuration. Prefer the built-in matcher or simple anchored character classes and bounded
quantifiers; avoid nested/ambiguous quantifiers, backreferences, and complex lookarounds. Applications that require
untrusted or dynamically supplied patterns need a separately sandboxed/linear-time matcher at another boundary;
rAPIdy's custom route syntax is not such a sandbox.
