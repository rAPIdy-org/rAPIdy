# Middlewares

## Описание

`Middleware` — это промежуточное ПО, позволяющее выполнять определённые действия до и после обработки запроса маршрутом.

```python
{!> ./docs/docs/server/middlewares/01_simple_middleware.py !}
```

!!! note "Порядок атрибутов"
    В веб-обработчике первым аргументом всегда передаётся `Request`, а вторым — `CallNext` (_обработчик запроса или `middleware` в цепочке_).
    *(Они имеют одинаковую сигнатуру — `rapidy.typedefs.CallNext`.)*

!!! note "Тип ответа обработчика"
    Ответ веб-обработчика или следующего `middleware` в цепочке всегда будет `StreamResponse`. Учитывайте это при проектировании ваших `middleware`.

---

## Способы создания

Создавать `middleware` можно двумя способами.

### Без параметров

Этот вариант подходит, если вам не нужно управлять запросом внутри `middleware`.

```python
{!> ./docs/docs/server/middlewares/02_create_without_parameters.py !}
```

### С параметрами

Используйте этот способ, если хотите более гибко управлять ответом на запрос.

```python
{!> ./docs/docs/server/middlewares/03_create_with_parameters.py !}
```

---

## Атрибуты

`Rapidy-middleware` поддерживают все механизмы валидации данных, доступные в веб-обработчиках, а также работу с ответами.

### Валидация

Как и веб-обработчики, `middleware` могут получать доступ к объектам запроса через атрибуты.

!!! tip "Перед тем как продолжить, рекомендуем ознакомиться с разделом [Request — Управление HTTP-запросом](../request), поскольку `middleware` используют такую же логику обработки параметров запроса."

!!! example "Обработка `Bearer`-токена."
    ```python
    {!> ./docs/docs/server/middlewares/04_validate.py !}
    ```

!!! info "Если вы извлекаете `body` как в `middleware`, так и в обработчике, ошибки о повторном чтении данных не возникнет."
    Данные кешируются в памяти и повторно используются при валидации.

---

### Управление ответом

Как и веб-обработчики, `middleware` могут управлять ответами через собственные атрибуты.

!!! tip "Перед тем как продолжить, рекомендуем ознакомиться с разделом [Response — Управление HTTP-ответом](../response), поскольку `middleware` используют ту же логику обработки ответов."

!!! note "Управление ответом возможно только в случае, если `middleware` возвращает необработанный тип данных *(любой, кроме `Response` или `StreamResponse`).*"

    ??? example "`Middleware` управляет ответом с помощью атрибутов."

        ```python hl_lines="11 15"
        {!> ./docs/docs/server/middlewares/05_response/01_response_management.py !}
        ```

    ??? example "`Middleware` не может управлять ответом с помощью атрибутов."

        ```python hl_lines="11 15"
        {!> ./docs/docs/server/middlewares/05_response/02_response_management.py !}
        ```

!!! info "Доступ к `Response`."
    ```python hl_lines="5"
    {!> ./docs/docs/server/middlewares/05_response/03_response_inject.py !}
    ```
    !!! warning "`Response` создаётся только для текущего `middleware`."

#### `Middleware` возвращает другой тип данных

Если `middleware` возвращает любой тип данных, кроме `StreamResponse`, укажите его в `Union`, чтобы `Rapidy` использовала этот тип при проверке ответов.

```python hl_lines="5"
{!> ./docs/docs/server/middlewares/05_response/04_response_diff_types.py !}
```
