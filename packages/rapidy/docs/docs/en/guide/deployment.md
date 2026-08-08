# Deployment

rAPIdy is an ASGI application. Install one server extra and point that server at `module:app`.

## Granian

Granian is the default used by `rapidy.run_app` and `python -m rapidy`.

```bash
pip install "rapidy[granian]"
granian --interface asgi \
  --host 0.0.0.0 --port 8000 \
  --workers 4 --workers-kill-timeout 30s \
  main:app
```

Equivalent Python entry point:

```python
from rapidy import run_app

run_app('main:app', host='0.0.0.0', port=8000, workers=4, workers_kill_timeout=30)
```

The CLI wrapper is also available:

```bash
python -m rapidy main:app --host 0.0.0.0 --port 8000 --workers 4 --workers-kill-timeout 30
```

## Uvicorn and Hypercorn

```bash
pip install "rapidy[uvicorn]"
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

pip install "rapidy[hypercorn]"
hypercorn --bind 0.0.0.0:8000 --workers 4 main:app
```

## Worker and shutdown model

Each worker is an independent process with its own lifespan and DI container. `Scope.APP` therefore means one
instance per worker, not one instance for the whole cluster. External databases, brokers, and caches must tolerate
that process model.

rAPIdy stops accepting new work through the server, closes accepted WebSockets with code 1001, and lets active HTTP
streams finish. Configure the server's graceful/kill timeout for the longest response you intend to allow. Do not use
the aiohttp Gunicorn worker from rAPIdy 1.x; it is not part of 2.0.

Access logs and TLS are server concerns. Put a reverse proxy or load balancer in front when you need centralized TLS,
timeouts, request-size policy, or cross-process balancing.
