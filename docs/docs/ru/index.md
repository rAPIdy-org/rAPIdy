---
hide:
  - navigation
  - toc
---

<style>
    .md-content .md-typeset h1 { display: none; }
</style>

<p align="center">
    <a href="https://github.com/daniil-grois/rAPIdy" target="blank">
        <img src="../assets/logo-teal.png" alt="rAPIdy">
    </a>
</p>

<p align="center">
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/dm/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Загрузки пакета">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/v/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2&label=pypi%20rAPIdy" alt="Версия пакета">
    </a>
    <a href="https://pypi.org/project/rapidy" target="blank">
        <img src="https://img.shields.io/pypi/pyversions/rapidy?style=flat&logo=rapidy&logoColor=%237e56c2&color=%237e56c2" alt="Поддерживаемые версии Python">
    </a>
    <a href="https://github.com/rAPIdy-org/rAPIdy/actions/workflows/test.yml?query=branch%3Amain" target="blank">
        <img src="https://github.com/rAPIdy-org/rAPIdy/actions/workflows/test.yml/badge.svg?branch=main?event=push" alt="Лицензия">
    </a>
    <a href="https://github.com/rAPIdy-org/rAPIdy/blob/main/LICENSE" target="blank">
        <img src="https://img.shields.io/badge/license-_MIT-%237e56c2?style=flat" alt="Лицензия">
    </a>
    <a href="https://docs.pydantic.dev/latest/" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v1.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V1">
    </a>
    <a href="https://docs.pydantic.dev/latest/" target="blank">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json&logoColor=%237e56c2&color=%237e56c2" alt="Pydantic V2">
    </a>
</p>

<p align="center">
    <i>
        <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a> -
        быстрый, легковесный и современный асинхронный веб-фреймворк,
        построенный на основе
        <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a>
        и
        <a href="https://github.com/pydantic/pydantic" target="blank">pydantic</a>.
    </i>
</p>

---

## 🚀 **Почему rAPIdy?**

rAPIdy создан для разработчиков, которым нужен быстрый, асинхронный веб-фреймворк, сочетающий производительность aiohttp
с простотой и современными возможностями таких фреймворков, как FastAPI.

Простой сервер на rAPIdy:
```python
from rapidy import Rapidy
from rapidy.http import get

@get("/")
async def hello() -> dict[str, str]:
    return {"message": "Hello, rAPIdy!"}

app = Rapidy(http_route_handlers=[hello])
```

---

## 🔥 **Ключевые возможности**

- Быстрый и легковесный – минимальные накладные расходы, построен на aiohttp
- Асинхронный – полностью асинхронный по своей сути
- Встроенная валидация – использует pydantic для валидации запросов
- Простой и гибкий – поддерживает как rAPIdy-стиль определения обработчиков, так и традиционные маршруты aiohttp
на функциях и классах
- Поддержка middleware – легко расширяйте функциональность с помощью middleware, включая встроенную валидацию
HTTP-параметров (заголовки, куки, параметры пути, параметры запроса и тело запроса).

---

## 📦 **Установка и настройка**

Установите rAPIdy через pip:
```shell
pip install rapidy
```

---

## 🏁 **Простой сервер**
```Python
{!> ./docs/index/simple_server.py !}
```

<span class="success-color">Успешная</span> валидация запроса
```bash
{!> ./docs/index/curl_correct__simple_server.sh !}
```
```text
{!> ./docs/index/curl_correct__response.txt !}
```

<span class="warning-color">Ошибка</span> валидации запроса
```bash
{!> ./docs/index/curl_incorrect__simple_server.sh !}
```
```text
{!> ./docs/index/curl_incorrect__response.txt !}
```

**Быстрый старт [Quickstart](quickstart)**<br/>
