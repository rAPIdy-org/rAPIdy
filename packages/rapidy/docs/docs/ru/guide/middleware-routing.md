# Middleware и mounts

Middleware образуют onion в порядке регистрации: первый — внешний. Middleware получает `Request` и `call_next`,
может валидировать Header/Cookie/Path/Query/Body, вернуть ответ без вызова хендлера или изменить готовый `Response`.

Декоратор `@middleware` принимает те же `response_*` настройки, что и HTTP-хендлер: status/content type,
валидацию, aliases, include/exclude, headers и cookies.

`HTTPRouter('/api', handlers, ...)` создаёт вложенное приложение со своими middleware, `client_max_size`, lifecycle-
хуками и lifespan. Роутеры можно вкладывать рекурсивно; DI-контейнер остаётся корневым. Регистрацию следует закончить
до startup, после него таблица роутов заморожена.

Рабочий пример middleware + mount:
[`examples/middleware_mounts.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/middleware_mounts.py).

## Production middleware

Готовый production stack собирается из типизированных объектов в `rapidy.middlewares`. Порядок регистрации совпадает
с request-порядком, первый middleware — внешний:

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
        HTTPSRedirectMiddleware(),
        RequestIDMiddleware(),
        CORSMiddleware(
            allow_origins=['https://console.example.com'],
            allow_methods=['GET', 'POST'],
            allow_headers=['authorization', 'content-type'],
            allow_credentials=True,
        ),
        CompressionMiddleware(algorithms=['br', 'gzip'], minimum_size=500),
    ],
)
```

`ProxyHeadersMiddleware` доверяет `Forwarded` и `X-Forwarded-*` только если непосредственный ASGI peer входит в
`trusted_proxies`, и идёт по цепочке адресов до первого недоверенного hop. Добавляйте сеть только тогда, когда каждый
proxy в ней перезаписывает или очищает forwarding headers. Нормализация proxy должна стоять раньше Trusted Host и
HTTPS redirect.

`TrustedHostMiddleware` принимает точные host names и шаблоны `*.example.com`, отклоняет отсутствующий, дублированный
или некорректный `Host`. `HTTPSRedirectMiddleware` сохраняет raw path/query и по умолчанию отвечает 307.

`RequestIDMiddleware` принимает один безопасный `X-Request-ID` или генерирует UUID, сохраняет `request_id` и
`request_context` в `request.state`, добавляет header и на framework errors и предоставляет `get_request_id()` /
`get_request_context()` через изолированный `ContextVar`. Контекст сохраняется во время чтения streaming iterable.

`CORSMiddleware` закрывает simple/preflight, regex origins, expose/max-age и explicit Private Network Access opt-in.
Credentialed CORS с wildcard origin/request headers/exposed headers запрещён при startup. PNA preflight разрешается
только при `allow_private_network=True`.

`CompressionMiddleware` согласует Brotli/gzip с учётом `q`, корректирует `Vary: Accept-Encoding`, `Content-Length` и
ETag. HEAD, Range/206, SSE, `no-transform`, бинарные media types и уже encoded ответы не меняются. `minimum_size`
относится к buffered response; подходящий streaming iterable сжимается инкрементально. Императивный поток
`prepare`/`write` получает CORS/request ID headers, но не сжимается после начала transport.

Gzip работает на стандартной библиотеке. Для `algorithms=['br', 'gzip']` установите `rapidy[brotli]`.
`GZipMiddleware` — gzip-only вариант. Совместимые параметры `response_zlib_executor` и
`response_zlib_executor_size` теперь управляют исполнением buffered compression при активном middleware, но сами по
себе сжатие не включают.

Полный исполняемый пример:
[`examples/production_middlewares.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/production_middlewares.py).
