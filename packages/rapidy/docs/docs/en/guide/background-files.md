# Background tasks and files

## Post-response work

`BackgroundTask` and `BackgroundTasks` run small in-process callables after the final response body frame. Attach a
single task or an ordered collection directly to a buffered or streaming response:

```python
from rapidy.background import BackgroundTasks
from rapidy.http import post, Response


async def notify(export_id: int) -> None:
    ...


@post('/exports')
async def create_export() -> Response:
    tasks = BackgroundTasks()
    tasks.add_task(notify, 20)
    return Response({'accepted': True}, status=202, background=tasks)
```

The lifecycle order is deterministic:

1. rAPIdy sends the final `http.response.body`, path-send, or zero-copy frame.
2. Tasks run sequentially in registration order. Synchronous functions run in a worker thread; asynchronous functions
   are awaited. Request context variables, including request IDs, are captured when each task is registered.
3. The request DI scope exits and its finalizers run.

The first task failure stops later tasks. It is logged because the HTTP response has already been committed. Request
cancellation propagates into the active task, stops the remaining tasks, and still unwinds DI. Tasks are awaited as
part of the request rather than detached, so an ASGI server's graceful request timeout also bounds them.
As with any thread-pool call, Python cannot forcibly stop a synchronous function that is already running; keep such
functions short and cooperative, or use an async implementation when cancellation must interrupt the work.

!!! warning
    This API is not a durable queue. A worker crash or forced shutdown can lose unfinished work. Use a broker-backed
    job system for retries, scheduling, cross-process coordination, or business-critical work.

## File responses

`FileResponse` is exported from `rapidy.responses`:

```python
from rapidy.http import get
from rapidy.responses import FileResponse


@get('/reports/latest')
async def report() -> FileResponse:
    return FileResponse('/srv/reports/latest.pdf', filename='report.pdf')
```

It provides `Content-Length`, `Content-Type`, `Accept-Ranges`, a strong `ETag`, `Last-Modified`, and optional
`Content-Disposition`. GET and HEAD share the same metadata. One `bytes` range is supported, including open-ended and
suffix ranges; valid ranges return 206 and unsatisfied ranges return 416. Multipart ranges are ignored and receive the
complete 200 representation. `If-None-Match` takes precedence over `If-Modified-Since`, and `If-Range` selects between
206 and the complete 200 representation.

When a server advertises the standard ASGI `http.response.pathsend` or `http.response.zerocopysend` extension,
rAPIdy uses it where its semantics fit. Other servers use bounded asynchronous file reads, so behavior does not depend
on a server-specific extension. File responses are not automatically compressed, which keeps ranges and validators
stable.

## Static files

Register `StaticFiles` like any other route object:

```python
from rapidy import Rapidy
from rapidy.staticfiles import StaticFiles


app = Rapidy(
    http_route_handlers=[
        StaticFiles(
            '/assets',
            directory='./public',
            html=True,
            cache_control='public, max-age=3600',
        )
    ]
)
```

The static router registers GET and automatic HEAD routes but stays out of OpenAPI. It rejects `..`, backslashes,
NULs, paths outside the configured root, and descendant symlinks by default. `follow_symlinks=True` permits a symlink
only when its resolved target remains inside that root. `html=True` serves `index.html` for directories and redirects
the directory URL to a trailing slash. `public=True` is the default; set `public=False` when application security must
protect the files.

`StaticFiles` also works inside `HTTPRouter` mounts. The configured root should contain application-owned files; use a
dedicated object store or reverse proxy when users can mutate the served tree.

The complete runnable application is
[`examples/background_files.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/background_files.py).
