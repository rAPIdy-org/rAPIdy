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

## `HTTPRouter` and mounts

`HTTPRouter(prefix, handlers, ...)` creates a nested application. Routers can be nested recursively and have their own
middleware, `client_max_size`, startup/shutdown/cleanup hooks, and lifespan contexts. Matching uses the longest mount
prefix. The request's `app` is rebound while the child handles it, while DI remains rooted in the parent container.

Routes are frozen at startup. Register handlers and mounts before the lifespan begins.
