# Развёртывание

rAPIdy — server-neutral ASGI-приложение. Базовая установка не содержит сервер:

```bash
pip install rapidy
```

Для встроенного launcher выберите Uvicorn:

```bash
pip install "rapidy[uvicorn]"
rapidy run main:app --host 0.0.0.0 --port 8000 \
  --workers 4 --timeout-graceful-shutdown 30
```

`rapidy dev main:app` включает reload и по умолчанию слушает `127.0.0.1`. Команды `rapidy run`, `rapidy dev`,
`python -m rapidy` и функция `run_app` используют Uvicorn. Для reload или нескольких workers передавайте import
string `main:app`, а не объект приложения.

Granian и Hypercorn остаются независимыми extras и не устанавливают Uvicorn:

```bash
pip install "rapidy[granian]"
granian --interface asgi --host 0.0.0.0 --port 8000 \
  --workers 4 --workers-kill-timeout 30s main:app

pip install "rapidy[hypercorn]"
hypercorn --bind 0.0.0.0:8000 --workers 4 main:app
```

Каждый worker — отдельный процесс со своим lifespan и DI-контейнером, поэтому APP-singleton является per-process.
При прямом application-lifespan shutdown rAPIdy запрашивает code 1001 для ещё открытых accepted WebSockets до
пользовательских shutdown hooks. Server может закрыть connections раньше и тогда сам определяет wire code: Uvicorn
делает orderly restart close, а Granian 2.8.1 пока имеет strict-xfail из-за abnormal 1006. Таймаут graceful shutdown
должен позволять активным stream-ответам завершиться. aiohttp Gunicorn worker из 1.x в 2.0 не поддерживается.
