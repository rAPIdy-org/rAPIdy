# Deployment

rAPIdy is a server-neutral ASGI application. The base installation contains no server:

```bash
pip install rapidy
```

Select Uvicorn for the built-in launcher:

```bash
pip install "rapidy[uvicorn]"
rapidy run main:app --host 0.0.0.0 --port 8000 \
  --workers 4 --timeout-graceful-shutdown 30
```

`rapidy dev main:app` uses the same runtime with reload enabled and binds to `127.0.0.1` by default.

## Uvicorn

`rapidy run`, `rapidy dev`, `rapidy.run_app`, and `python -m rapidy` use Uvicorn's programmatic API. The equivalent
Python entry point is:

```python
from rapidy import run_app

run_app('main:app', host='0.0.0.0', port=8000, workers=4, timeout_graceful_shutdown=30)
```

Reload and multiple workers require an import string such as `main:app`; a direct application object remains valid
for a single non-reloading process.

## Granian and Hypercorn

Alternative server extras do not pull in Uvicorn and are launched through their native CLIs:

```bash
pip install "rapidy[granian]"
granian --interface asgi --host 0.0.0.0 --port 8000 --workers 4 main:app

pip install "rapidy[hypercorn]"
hypercorn --bind 0.0.0.0:8000 --workers 4 main:app
```

## Worker and shutdown model

Each worker is an independent process with its own lifespan and DI container. `Scope.APP` therefore means one
instance per worker, not one instance for the whole cluster. External databases, brokers, and caches must tolerate
that process model.

The process server stops accepting new work. During direct application-lifespan shutdown rAPIdy requests code 1001
for accepted WebSockets that are still open, before user shutdown hooks, and lets active HTTP streams finish. A server
may close connections before sending lifespan shutdown and then owns the wire code; Uvicorn currently uses its
orderly restart close, while Granian 2.8.1 has a tracked strict-xfail because it drops the socket as 1006. Configure
the server's graceful/kill timeout for the longest response you intend to allow. Do not use the aiohttp Gunicorn
worker from rAPIdy 1.x; it is not part of 2.0.

Access logs and TLS are server concerns. Put a reverse proxy or load balancer in front when you need centralized TLS,
timeouts, request-size policy, or cross-process balancing.
