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

## Повторяющиеся query/header значения

Семантика повторяющихся query parameters и header fields определяется Python-аннотацией. Коллекция — например,
`list[str]`, `tuple[int, ...]` или `set[str]` — получает все физические значения в wire order до преобразования
Pydantic. Scalar получает одно значение, а повторения отклоняются с HTTP 422 и ошибкой `duplicate_parameter`.
Это же правило действует для полей валидируемых моделей `QueryParams()`/`Headers()` и для аннотации значения
валидируемого mapping, например `dict[str, list[str]]`.

rAPIdy не разбивает текст по запятым: `?tag=a&tag=b` — повторяющийся input, а `?tag=a,b` — одна строка. Raw plural
containers с `validate=False` сохраняют нативное поведение multidict.

`Body()` по умолчанию ожидает JSON; также поддержаны text, bytes, urlencoded и multipart. Обычные тела и urlencoded-
формы ограничиваются `client_max_size`, который по умолчанию равен 1 МиБ (`1024**2` байт). Для multipart действует
независимая политика `MultipartLimits`, поэтому
файловые загрузки можно разрешить, не ослабляя защиту JSON и произвольных raw body:

```python
from rapidy import Rapidy
from rapidy.request import MultipartLimits

app = Rapidy(
    client_max_size=1024**2,
    multipart_limits=MultipartLimits(
        max_body_size=16 * 1024**2,
        max_parts=1000,
        max_fields=1000,
        max_files=100,
        max_field_size=1024**2,
        max_file_size=8 * 1024**2,
        spool_threshold=1024**2,
    ),
)
```

Multipart разбирается по мере получения ASGI-чанков. Полное исходное multipart-тело и загружаемые файлы после
`spool_threshold` переносятся из памяти во временный файл; текстовые поля остаются в памяти, но ограничены
`max_field_size`. Все лимиты должны быть положительными целыми числами, превышение возвращает HTTP 413.
`Request.read()` продолжает соблюдать `client_max_size`, даже если `post()` уже принял multipart-форму. Полученные
файлы представлены `rapidy.request.FileField`; сохранённые файлы должен закрывать потребитель. Потоковая инъекция
request body из 1.x удалена.

Ошибка валидации возвращает HTTP 422 и JSON-массив `errors`; превышение размера тела остаётся HTTP 413.
Аннотация возвращаемого значения задаёт схему ответа, а `response_*` аргументы декоратора управляют валидацией,
include/exclude, alias, status, content type, заголовками и cookie.

Исполняемый пример: [`examples/parameters.py`](https://github.com/rAPIdy-org/rAPIdy/blob/main/packages/rapidy/examples/parameters.py).
