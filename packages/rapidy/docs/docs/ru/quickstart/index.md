---
hide:
  - navigation
---

# Быстрый старт
## Создание простых обработчиков
<a href="https://github.com/daniil-grois/rAPIdy" target="_blank">rAPIdy</a>
базируется на
<a href="https://github.com/aio-libs/aiohttp" target="_blank">aiohttp</a>
и поддерживает все варианты определения обработчиков.<br/>
Ниже будут показаны лишь основные.
!!! tip "Все способы определения можно посмотреть **[здесь](../docs/server/handlers)**"

### Функциональные обработчики
```Python hl_lines="4"
{!> ./docs/quickstart/01_func_handler.py !}
```
??? example "Регистрация без декоратора"
    ```Python hl_lines="9"
    {!> ./docs/quickstart/02_func_handler_no_deco.py !}
    ```

---

### Классовые обработчики
```Python hl_lines="4"
{!> ./docs/quickstart/03_controller_handler.py !}
```

??? example "Регистрация без декоратора"
    ```Python hl_lines="15"
    {!> ./docs/quickstart/04_controller_handler_no_deco.py !}
    ```

## Middleware
Middleware — это промежуточные компоненты, которые обрабатывают запросы и ответы на уровне веб-фреймворка.

Они позволяют выполнять дополнительные действия до и/или после обработки запроса основным обработчиком.

```Python hl_lines="2 3 5 16"
{!> ./docs/quickstart/05_middleware.py !}
```

!!! info "Примечание"
    В middleware-обработчике
    <b><span class="note-color">первым аргументом</span></b>
    всегда должен быть <span class="note-color">Request</span>, а вторым — <span class="note-color">call_next</span>.

## HTTPRoute
`HTTPRoute` позволяет регистрировать группы обработчиков и играет ключевую роль в маршрутизации (routing),
помогая направлять запросы к нужным обработчикам в зависимости от HTTP-метода, пути, параметров и других условий.

!!! info "`HTTPRoute` регистрируется точно так же, как и любой HTTP-обработчик."

```Python hl_lines="14 16"
{!> ./docs/quickstart/06_router.py !}
```

??? example "Регистрация обработчиков в роутере без декоратора"
    ```Python hl_lines="15 16 20"
    {!> ./docs/quickstart/07_router_no_deco.py !}
    ```

??? example "Полный пример регистрации роутера и обработчиков"
    ```Python hl_lines="24 28 29 30"
    {!> ./docs/quickstart/08_router_full_example.py !}
    ```

## Пример простой валидации
```Python hl_lines="6 19 25 28"
{!> ./docs/quickstart/09_validation.py !}
```

## Запуск веб-сервера
### Простой запуск
Скопируйте код в файл `main.py`.
```Python hl_lines="12"
{!> ./docs/quickstart/10_runserver/run_app.py !}
```

Запустите сервер в режиме реального времени:
```bash
{!> ./docs/quickstart/10_runserver/run_app.sh !}
```

!!! note "Также вы можете указать различные параметры запуска, например, `host` или `port`."
    ```python
    {!> ./docs/quickstart/10_runserver/run_app_change_host_and_port.py !}
    ```

### WSGI-запуск (Gunicorn)
<span class="green-color">Gunicorn</span> — это Python WSGI HTTP-сервер для UNIX.

??? note "Что такое WSGI"
    WSGI (Web Server Gateway Interface — интерфейс шлюза Web-сервера) —
    это простой и универсальный интерфейс взаимодействия между Web-сервером и Web-приложением,
    впервые описанный в <a href="http://www.python.org/dev/peps/pep-0333/" target="_blank">PEP-333</a>.

!!! note "Подробнее про <a href="https://gunicorn.org/" target="_blank">gunicorn.org</a>"

Добавьте Gunicorn в ваш проект:

```bash
pip install gunicorn
```

Скопируйте код в файл `main.py`.
```Python hl_lines="6"
{!> ./docs/quickstart/10_runserver/gunicorn.py !}
```

Запустите команду в консоли:
```bash
{!> ./docs/quickstart/10_runserver/gunicorn.sh !}
```

Команда `gunicorn main:rapidy` обращается к:

* `main`: файл `main.py` (модуль Python).
* `rapidy`: объект, созданный внутри файла `main.py` в строке `rapidy = Rapidy()`.
* `--reload`: перезапускает сервер после изменения кода. Используйте только для разработки.
