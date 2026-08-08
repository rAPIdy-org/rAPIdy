# Управление HTTP-ошибками

## Описание

**HTTP-ошибки** — это объекты с определённой логикой, которые могут возвращать ответ веб-сервера с предопределённым `HTTP-кодом`.

!!! info "Ошибки вызываются с помощью конструкции `raise`."

```python hl_lines="6"
{!> ./docs/docs/server/http_errors/01_handler_raise_400/example.py !}
```

**HTTP-ошибки** могут быть вызваны как разработчиком, так и самим веб-сервером `Rapidy`, если клиент или сервер совершат ошибку.

!!! info "Все ошибки находятся в модуле `rapidy.web_exceptions`, но их также можно импортировать из `rapidy.http`."

## Виды HTTP-ошибок

`Rapidy` поддерживает четыре типа **HTTP-ошибок**:

- **2xx** — успешные ответы *(базовый класс — `HTTPSuccessful`)*
- **3xx** — перенаправления *(базовый класс — `HTTPRedirection`)*
- **4xx** — ошибки клиента *(базовый класс — `HTTPClientError`)*
- **5xx** — ошибки сервера *(базовый класс — `HTTPServerError`)*

!!! tip "Базовые классы можно использовать для обработки всех дочерних ошибок."
!!! info "Подробнее о **HTTP-ошибках** можно прочитать в документации `aiohttp` **<a href='https://docs.aiohttp.org/en/stable/_modules/aiohttp/web_exceptions.html' target='_blank'>здесь</a>**."

## Вызов HTTP-ошибок

### Вызов HTTP-ошибки разработчиком

Разработчик может вызвать ошибку самостоятельно, если обработка запроса идёт по неуспешному сценарию.

```python hl_lines="6"
{!> ./docs/docs/server/http_errors/01_handler_raise_400/example.py !}
```

```bash
{!> ./docs/docs/server/http_errors/01_handler_raise_400/curl.sh !}
```

```text
{!> ./docs/docs/server/http_errors/01_handler_raise_400/curl__response.txt !}
```

### Вызов HTTP-ошибки веб-сервером

Веб-сервер вызовет ошибку автоматически, если запрос не может быть обработан.

??? example "Not Found — `404`"
    ```python
    {!> ./docs/docs/server/http_errors/02_handler_not_found/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/http_errors/02_handler_not_found/curl.sh !}
    ```
    ```text
    {!> ./docs/docs/server/http_errors/02_handler_not_found/curl__response.txt !}
    ```

??? example "Method Not Allowed — `405`"
    ```python
    {!> ./docs/docs/server/http_errors/03_method_not_allowed/example.py !}
    ```
    ```bash
    {!> ./docs/docs/server/http_errors/03_method_not_allowed/curl.sh !}
    ```
    ```text
    {!> ./docs/docs/server/http_errors/03_method_not_allowed/curl__response.txt !}
    ```

#### Ошибка валидации (Validation Error)

При неуспешной валидации веб-запроса клиент получит ответ в формате `application/json` с описанием ошибки.

```python
{!> ./docs/docs/server/http_errors/04_request_validation_failure/example.py !}
```
```bash
{!> ./docs/docs/server/http_errors/04_request_validation_failure/curl.sh !}
```
```text
{!> ./docs/docs/server/http_errors/04_request_validation_failure/curl__response.txt !}
```

!!! info "HTTP-ошибка `HTTPValidationFailure` содержит список ошибок в поле `validation_errors`."

    Чтобы получить доступ к этим ошибкам, можно перехватить `HTTPValidationFailure`:
    ```python
    {!> ./docs/docs/server/http_errors/05_catch_422/01_example.py !}
    ```

!!! info "`HTTPValidationFailure` наследуется от `HTTPUnprocessableEntity`."
    Это значит, что обе ошибки можно обработать через `HTTPUnprocessableEntity`, если не требуется раскрывать клиенту подробности ошибки.
    ```python
    {!> ./docs/docs/server/http_errors/05_catch_422/02_example.py !}
    ```

## Перехват ошибок

Иногда требуется перехватить ошибку, например, чтобы изменить ответ сервера.

Для этого можно использовать `middleware`:

```python
{!> ./docs/docs/server/http_errors/06_catch_422_middleware.py !}
```

??? example "Пример обработки всех ошибок с унифицированным ответом"

    ```python
    {!> ./docs/docs/server/http_errors/07_catch_422_middleware_full.py !}
    ```
