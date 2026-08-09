# Migrating from rAPIdy 1.x to 2.0

rAPIdy 1.x → 2.0: `import rapidy` is preserved. The root package, `rapidy.http`, and
`rapidy.depends` are not renamed. The breaking changes are limited to the transport layer:
Request/Response objects, HTTP exceptions, WebSockets, `run_app`, and worker management.

### 01. Request

`Request` is now an ASGI-backed value object. The public request-data contract is preserved:
`method`, `path`, `path_params`, `query`, `headers`, `cookies`, `body_exists`, `read()`,
`text()`, `json(loads=...)`, `post()`, `content_type`, `charset`, `app`, and `state`.

**Before**

```python
request['trace_id'] = trace_id
trace_id = request['trace_id']
url = request.rel_url
transport = request.transport
copy = request.clone()
```

**After**

```python
request.state.trace_id = trace_id
trace_id = request.state.trace_id
url = request.path, request.query
```

Use `request.state` for request-local data. `transport` and `clone()` have no equivalent.

### 02. Response, HTTP exceptions, and StreamResponse

Ordinary responses and HTTP exceptions are value objects rendered by the framework. Normal
`Response.prepare()` and `enable_compression()` are removed. The `zlib_executor` and
`zlib_executor_size` arguments are accepted for signature compatibility but do not enable
compression. HTTP exceptions retain mutable headers, but no longer inherit response-only APIs.

**Before**

```python
response = Response(text='ready', zlib_executor_size=1024)
response.enable_compression()
await response.prepare(request)
```

**After**

```python
response = Response(text='ready')

async def chunks():
    yield b'first\n'
    yield b'second\n'

stream = StreamResponse(body=chunks())
```

`StreamResponse` also keeps the imperative `prepare()`, `write()`, and `write_eof()` flow for
code that needs explicit streaming control.

### 03. run_app and Granian options

`run_app` now delegates to Granian. Server-specific keyword arguments must use Granian's
programmatic API names.

**Before**

```python
run_app(
    app,
    host='0.0.0.0',
    port=8000,
    access_log=logger,
    ssl_context=ssl_context,
    shutdown_timeout=30,
    reuse_port=True,
)
```

**After**

```python
run_app(
    app,
    host='0.0.0.0',
    port=8000,
    workers=2,
    workers_kill_timeout=30,
)
```

In particular, `shutdown_timeout` becomes Granian's `workers_kill_timeout`. Pass other runtime
settings using the corresponding Granian keyword arguments.

### 04. Gunicorn workers

The `GunicornWebWorker` and `GunicornUVLoopWebWorker` exports are removed. Multi-process serving
is configured directly through `run_app`.

**Before**

```shell
gunicorn app:app --worker-class rapidy.GunicornWebWorker --workers 4
```

**After**

```python
from rapidy import run_app

run_app(app, workers=4)
```

The dishka application container is created once per process, not once for the whole worker
cluster. Providers that manage external resources must therefore be safe to initialize in each
worker.

### 05. Streaming request bodies

The inherited `StreamReader`, `DataQueue`, `FlowControlDataQueue`, `EofStream`, and
`EMPTY_PAYLOAD` APIs are removed.

**Before**

```python
@post('/upload')
async def upload(body: StreamReader = Body()) -> None:
    async for chunk in body:
        await store(chunk)
```

**After**

```python
@post('/upload')
async def upload(body: bytes = Body()) -> None:
    await store(body)
```

There is no streaming-request-body equivalent in 2.0. `Body()` reads the complete body into
memory, so enforce appropriate request-size limits and move very large uploads to dedicated
storage endpoints when necessary.

### 06. WebSockets

WebSockets use a dedicated ASGI handler instead of returning an inherited response from an HTTP
route. `WebSocketResponse`, `WebSocketReady`, and `WSMsgType` are removed.

**Before**

```python
@get('/ws/{room}')
async def chat(request: Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for message in ws:
        await ws.send_str(message.data)
    return ws
```

**After**

```python
@websocket('/ws/{room}')
async def chat(ws: WebSocket, room: str = PathParam()):
    await ws.accept()
    async for message in ws:
        await ws.send_text(message)
```

### 07. cleanup_ctx and lifespan

Application cleanup contexts move to the ASGI lifespan interface.

**Before**

```python
app.cleanup_ctx.append(database_context)
```

**After**

```python
app.lifespan.append(database_context)

# Or at construction time:
app = Rapidy(lifespan=[database_context])
```

### 08. Route registration, signals, and lifecycle methods

Inherited router mutation, response signals, and direct lifecycle methods are replaced by
rAPIdy's route, middleware, and lifespan APIs.

**Before**

```python
app.add_routes([route])
app.router.add_get('/items', list_items)
app.router.add_post('/items', create_item)
app.router.add_view('/items/{item_id}', ItemView)
app.on_response_prepare.append(add_headers)
await app.startup()
await app.shutdown()
await app.cleanup()
```

**After**

```python
@get('/items')
async def list_items(): ...

@post('/items')
async def create_item(): ...

router = HTTPRouter('/v1', [list_items, create_item])
app = Rapidy(http_route_handlers=[router], middleware=[add_headers])
app.add_http_router(another_router)
app.add_http_routers([admin_router, health_router])
```

Use middleware instead of response-prepare signals. Startup and shutdown are driven by ASGI
lifespan; register resource contexts through `lifespan` rather than calling lifecycle methods.

### 09. Static files

Inherited `app.router.add_static(...)`, `static`, and `FileResponse` serving are outside the 2.0
scope.

**Before**

```python
app.router.add_static('/assets', './assets')
return FileResponse('./downloads/report.pdf')
```

**After**

```nginx
location /assets/ {
    root /srv/application;
}
```

There is no framework equivalent in 2.0. Serve static assets and downloads through a reverse
proxy, object storage, or a CDN.

### 10. BackgroundTasks

**After**

```python
@post('/reports')
async def create_report(job: ReportJob = Body()) -> Response:
    await broker.publish('reports', job.model_dump())
    return Response(status_code=202)
```

rAPIdy has no `BackgroundTasks` abstraction. Use your own task primitives for small in-process
work and a durable broker or job queue for important background work.

### 11. AppKey and NotAppKeyWarning

The inherited typed `AppKey` mechanism and `NotAppKeyWarning` are removed. String mapping keys
remain as an alias over application state.

**Before**

```python
DATABASE = AppKey('database', Database)
app[DATABASE] = database
database = app[DATABASE]
```

**After**

```python
app['database'] = database
database = app['database']

# Equivalent attribute form:
app.state.database = database
```

### 12. Deprecated application arguments

`logger` and `handler_args` remain accepted by the application constructor only as no-op
compatibility arguments. Each produces `DeprecationWarning` and may be removed in a future
version.

**Before**

```python
app = Application(logger=logger, handler_args={'expect_handler': expect_handler})
```

**After**

```python
app = Rapidy(http_route_handlers=routes)
```

Configure server logging through `run_app`/Granian settings and express handler behavior through
route handlers or middleware.

### 13. Authentication and authorization

OpenAPI security metadata remains documentation-only until runtime security is explicitly installed. Applications
that previously implemented authentication in middleware or DI can migrate incrementally to `SecurityConfig`.

```python
from rapidy.security import APIKeyAuth, SecurityConfig

security = SecurityConfig(
    schemes=[APIKeyAuth(key=settings.api_key)],
    requirements=[{'apiKey': []}],
)
app = Rapidy(security=security, openapi_config=OpenAPIConfig())
```

The same requirements now enforce HTTP and WebSocket access and generate OpenAPI security metadata. Use route-level
`security=...` for overrides, `security=[]` to remove authentication while retaining guards, or `public=True` to
remove both inherited authentication and guards. `request.user`, `request.auth`, and `request.identity` replace
middleware-specific request-state conventions; `SecurityIdentity` and `AuthCredentials` are also available through
typed DI.
