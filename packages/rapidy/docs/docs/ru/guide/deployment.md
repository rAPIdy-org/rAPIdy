# Развёртывание

rAPIdy — ASGI-приложение. Установите extra выбранного сервера и укажите `module:app`.

```bash
# Granian — основной вариант
pip install "rapidy[granian]"
granian --interface asgi --host 0.0.0.0 --port 8000 \
  --workers 4 --workers-kill-timeout 30s main:app

# Uvicorn
pip install "rapidy[uvicorn]"
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Hypercorn
pip install "rapidy[hypercorn]"
hypercorn --bind 0.0.0.0:8000 --workers 4 main:app
```

`run_app` и `python -m rapidy` используют Granian. Каждый worker — отдельный процесс со своим lifespan и DI-
контейнером, поэтому APP-singleton является per-process. Таймаут graceful shutdown должен позволять активным stream-
ответам завершиться. aiohttp Gunicorn worker из 1.x в 2.0 не поддерживается.
