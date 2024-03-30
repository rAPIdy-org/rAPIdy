---
hide:
  - navigation
---

# Quickstart

## Создание простых обработчиков

!!! info "Примечание"
    <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a>
    базируется на
    <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a>
    и поддерживает все варианты определения обработчиков.<br/>
    Ниже будут показаны лишь основные.

### Функциональные обработчики

```Python
{!> ./quickstart/ex_func_handler_01.py !}
```

??? example "Второй способ"
    ```Python hl_lines="7"
        {!> ./quickstart/ex_func_handler_02.py !}
    ```

---

### Классовые обработчики

```Python
{!> ./quickstart/ex_class_handler.py !}
```

## Middleware

```Python hl_lines="4 15"
{!> ./quickstart/ex_middleware.py !}
```

!!! info "Примечание"
    В middleware обработчике
    <b><span class="note-color">первым аргументом</span></b>
    всегда должен быть <span class="note-color">web.Request</span>, а вторым <span class="note-color">handler</span>.


## Пример простой валидации

```Python hl_lines="7 20 25 28"
{!> ./quickstart/ex_validation.py !}
```

!!! tip "Совет"
    **Больше примеров валидации [Examples](examples.md)**

## Запуск веб-сервера

### Простой запуск

Скопируйте в файл `main.py`.
```Python hl_lines="10"
{!> ./quickstart/ex_runserver_simple.py !}
```

Запустите сервер в режиме реального времени:
```bash
{!> ./quickstart/ex_runserver_simple.sh !}
```

!!! note "Также вы можете указать различные параметры запуска, например, `host` или `port`"
    ```python
    web.run_app(app, host='0.0.0.0', port=8080)
    ```

### WSGI запуск (gunicorn)
<span class="green-color">Gunicorn</span> это Python WSGI HTTP-сервер для UNIX. 

??? note "Что такое WSGI"
    WSGI (расшифровывается как Web Server Gateway Interface — интерфейс шлюза Web-сервера) — 
    это простой и универсальный интерфейс взаимодействия между Web-сервером и Web-приложением, 
    впервые описанный в <a href="http://www.python.org/dev/peps/pep-0333/" target="blank">PEP-333</a>. 

!!! note "Подробнее про <a href="https://gunicorn.org/" target="blank">gunicorn.org</a>"

Добавьте gunicorn в ваш проект

```bash
pip install gunicorn
```

Скопируйте в файл `main.py`.
```Python hl_lines="6"
{!> ./quickstart/ex_runserver_gunicorn.py !}
```

Запустите команду в консоли:
```bash
{!> ./quickstart/ex_runserver_gunicorn.sh !}
```

Команда `gunicorn main:app` обращается к:

* `main`: файл `main.py` (модуль Python).
* `app`: объект, созданный внутри файла `main.py` в строке `app = web.Application()`.
* `--reload`: перезапускает сервер после изменения кода. Используйте только для разработки.
