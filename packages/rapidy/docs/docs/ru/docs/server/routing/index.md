<!-- RAPIDY_LEGACY_1X -->

> **⚠️ Историческая документация rAPIdy 1.x.** Страница сохранена только для справки и может описывать aiohttp API, которых нет в rAPIdy 2.0. Для нового кода используйте [актуальную документацию 2.0](https://rapidy.dev/).

# Маршрутизация HTTP-запросов

## Описание
Маршрутизация в `Rapidy` позволяет управлять обработкой HTTP-запросов, сопоставляя их с соответствующими обработчиками.

## Определение маршрутов
Простейший способ определения маршрутов — использование декораторов `get`, `post`, `put`, `delete`, `head`, `options`.

```python
from rapidy.http import get, post, put, delete, head, options

@get('/')
async def get_handler() -> ...:
    ...

@post('/')
async def post_handler() -> ...:
    ...

@put('/')
async def put_handler() -> ...:
    ...

@delete('/')
async def delete_handler() -> ...:
    ...

@head('/')
async def head_handler() -> ...:
    ...

@options('/')
async def options_handler() -> ...:
    ...
```
