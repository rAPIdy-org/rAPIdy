# Наблюдаемость и developer experience

## Структурированные access logs

`AccessLogMiddleware` оборачивает итоговое ASGI-приложение и создаёт один `AccessLogRecord` при завершении HTTP-ответа
или WebSocket-сессии:

```python
from rapidy import Rapidy
from rapidy.observability import AccessLogMiddleware

rapidy_app = Rapidy(http_route_handlers=routes)
app = AccessLogMiddleware(rapidy_app)
```

Запись содержит протокол, метод, шаблон найденного маршрута, status, latency, размеры запроса/ответа, request ID,
trace ID и WebSocket close code. Конкретный path, query string, заголовки, credentials и значения path-параметров в
неё не попадают. Все ненайденные пути используют стабильную метку `{unmatched}`. Для компактного JSON доступен
`JSONAccessFormatter` из `rapidy.observability`; callback `emit` позволяет синхронно поставить запись в очередь.

`RequestIDMiddleware` внутри приложения заполняет `request_id`. Из корректного W3C `traceparent` берётся только trace
ID, полный заголовок не сохраняется.

## OpenTelemetry

OpenTelemetry остаётся опциональным:

```bash
pip install "rapidy[otel]"
```

```python
from rapidy.observability import instrument_app

app = instrument_app(rapidy_app, tracer_provider=tracer_provider, meter_provider=meter_provider)
```

Обёртка использует официальную OpenTelemetry ASGI instrumentation для HTTP/WS spans и metrics. Имена spans и
`http.route` строятся по шаблонам, например `GET /users/{user_id}`. Захват server request/response headers по умолчанию
отключён. Exporters и providers настраивает приложение.

## Problem Details и обработчики исключений

Реестры handlers локальны для приложений и наследуются через mounts. Побеждает наиболее конкретный handler самого
глубокого sub-application:

```python
from rapidy import Rapidy
from rapidy.exceptions import HTTPException
from rapidy.problems import ProblemDetailsRenderer

app = Rapidy(
    exception_handlers={
        HTTPException: ProblemDetailsRenderer(type_base_url='https://api.example.com/problems'),
        DomainError: ProblemDetailsRenderer(),
    },
)
```

`ProblemDetailsRenderer` формирует RFC 9457 `application/problem+json`; детали неожиданных исключений скрыты. После
начала ответа handlers не вызываются — rAPIdy только безопасно завершает текущий stream. Пользовательский handler
может быть sync/async и обязан вернуть `Response` или `StreamResponse`.

## Именованные маршруты и reverse URLs

```python
@get('/users/{user_id:\\d+}', name='user.detail')
async def user(user_id: int = PathParam()): ...

app.url_for('user.detail', user_id=42)       # /users/42
request.url_for('user.detail', user_id=42)   # учитывает ASGI root_path
```

Для missing, unexpected, invalid, unknown и ambiguous параметров reverse lookup поднимает типизированные ошибки.
У `StaticFiles('/assets', name='assets', ...)` доступен `app.static_url('assets', 'js/app.js')`; корневой маршрут
называется `assets:index`.

## CLI и стандартные пути документации

```bash
rapidy dev main:app --reload
rapidy run main:app --host 0.0.0.0 --port 8080
rapidy routes main:rapidy_app
rapidy check main:rapidy_app
```

`routes --json` подходит для автоматизации. `check` показывает routes, names, mounts и OpenAPI config, но не выводит
application state или environment. Старый вызов `python -m rapidy main:app` по-прежнему означает `run`.

OpenAPI остаётся opt-in. Preset стандартных путей включается явно:

```python
app = Rapidy(openapi_config=OpenAPIConfig.docs(title='Users API', version='1'))
```

После этого доступны `/openapi.json`, `/docs` и `/redoc`.
