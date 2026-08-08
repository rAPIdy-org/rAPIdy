# Параметры и валидация

rAPIdy один раз анализирует сигнатуру хендлера при регистрации роута и извлекает значения из объявленных HTTP-
источников. Pydantic v2 выполняет преобразование и валидацию до вызова хендлера.

| Marker | Источник | Пример |
|---|---|---|
| `PathParam` | Шаблон пути | `item_id: int = PathParam()` |
| `QueryParam` | Query string | `page: int = QueryParam(alias='p')` |
| `Header` | Заголовок | `token: str = Header(alias='X-Token')` |
| `Cookie` | Cookie | `session: str = Cookie()` |
| `Body` | Тело запроса | `payload: Model = Body()` |

`Body()` по умолчанию ожидает JSON; также поддержаны text, bytes, urlencoded и multipart. `Request.read()`, `text()`,
`json()` и `post()` используют общий кэш тела и соблюдают `client_max_size`. Потоковая инъекция request body из 1.x
удалена.

Ошибка валидации возвращает HTTP 422 и JSON-массив `errors`; превышение размера тела остаётся HTTP 413.
Аннотация возвращаемого значения задаёт схему ответа, а `response_*` аргументы декоратора управляют валидацией,
include/exclude, alias, status, content type, заголовками и cookie.

Исполняемый пример: [`examples/parameters.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/parameters.py).
