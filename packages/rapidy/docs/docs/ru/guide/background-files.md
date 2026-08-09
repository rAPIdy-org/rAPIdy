# Background tasks и файлы

## Работа после ответа

`BackgroundTask` и `BackgroundTasks` выполняют небольшие in-process функции после последнего body frame. Одну задачу
или упорядоченный набор можно прикрепить к обычному или streaming response:

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

Порядок lifecycle фиксирован:

1. rAPIdy отправляет последний `http.response.body`, path-send или zero-copy frame.
2. Задачи выполняются последовательно в порядке регистрации. Синхронные функции уходят в worker thread,
   асинхронные await-ятся. Context variables запроса, включая request ID, захватываются при регистрации.
3. Закрывается REQUEST-scope DI и выполняются его финализаторы.

Первая ошибка останавливает оставшиеся задачи и логируется: HTTP response к этому моменту уже отправлен. Cancellation
передаётся активной задаче, останавливает очередь и не мешает DI cleanup. Задачи не detached, поэтому они входят в
request lifetime и ограничиваются graceful request timeout ASGI-сервера.
Как и для любого thread-pool вызова, Python не может принудительно остановить уже выполняющуюся синхронную функцию;
такая функция должна быть короткой и cooperative, а для прерываемой работы лучше использовать async-реализацию.

!!! warning
    Это не durable queue. При аварии worker или принудительном shutdown незавершённая работа может потеряться. Для
    retries, schedule, межпроцессной координации и критичных операций нужен broker-backed job system.

## FileResponse

`FileResponse` экспортируется из `rapidy.responses`:

```python
from rapidy.http import get
from rapidy.responses import FileResponse


@get('/reports/latest')
async def report() -> FileResponse:
    return FileResponse('/srv/reports/latest.pdf', filename='report.pdf')
```

Response выставляет `Content-Length`, `Content-Type`, `Accept-Ranges`, сильный `ETag`, `Last-Modified` и при
необходимости `Content-Disposition`. GET и HEAD используют одинаковые metadata. Поддерживается один `bytes` range,
включая open-ended и suffix: валидный диапазон даёт 206, недоступный — 416. Multipart range игнорируется и получает
полную 200 representation. `If-None-Match` имеет приоритет над `If-Modified-Since`, а `If-Range` выбирает между 206 и
полной 200 representation.

Если сервер объявил стандартное ASGI extension `http.response.pathsend` или `http.response.zerocopysend`, rAPIdy
использует его там, где сохраняется семантика. На остальных серверах работает переносимый fallback с ограниченными
асинхронными чтениями. Файловые ответы автоматически не сжимаются — так ranges и validators остаются стабильными.

## StaticFiles

Static router регистрируется как обычный route object:

```python
from rapidy import Rapidy
from rapidy.staticfiles import StaticFiles


app = Rapidy(
    http_route_handlers=[
        StaticFiles('/assets', directory='./public', html=True)
    ]
)
```

Он создаёт GET и автоматический HEAD, но не попадает в OpenAPI. По умолчанию отклоняются `..`, обратные слеши, NUL,
выход за configured root и symlink в дочерних компонентах. `follow_symlinks=True` разрешает ссылку только при условии,
что resolved target остаётся внутри root. `html=True` отдаёт `index.html` для каталогов и перенаправляет URL каталога
на вариант с завершающим `/`. Default cache header — `public, max-age=3600`. По умолчанию route публичный; используйте
`public=False`, если файлы должна защищать application security.

`StaticFiles` совместим с mount через `HTTPRouter`. Configured root должен содержать доверенные файлы приложения; для
изменяемого пользователями дерева лучше использовать object storage или reverse proxy.

Полный исполняемый пример:
[`examples/background_files.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/background_files.py).
