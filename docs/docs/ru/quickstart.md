# Quickstart

## Создание простых обработчиков

!!! info "Примечание"
    <a href="https://github.com/daniil-grois/rAPIdy" target="blank">rAPIdy</a>
    базируется на
    <a href="https://github.com/aio-libs/aiohttp" target="blank">aiohttp</a>
    и поддерживает все варианты определения обработчиков.

### Функциональные обработчики

!!! info "Примечание"
    В функциональном обработчике
    <b><span class="note-color">первым аргументом</span></b>
    всегда должен быть <span class="note-color">web.Request</span>.

<details open>
<summary>Первый способ</summary>

```Python
from rapidy import web

routes = web.RouteTableDef()

@routes.post('/')
async def handler(request: web.Request) -> web.Response:
    return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```
</details>

<details>
<summary>Второй способ</summary>

```Python hl_lines="7"
from rapidy import web

async def handler(request: web.Request) -> web.Response:
    return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes([web.post('/', handler)])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)

```
</details>

---

### Классовые обработчики

<details open>
<summary>Первый способ</summary>

```Python
from rapidy import web

class Handler(web.View):
    async def get(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def post(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def put(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def patch(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def delete(self) -> web.Response:
        return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes([web.view('/', Handler)])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```
</details>

<details>
<summary>Второй способ</summary>

```Python hl_lines="22 23 24 25 26"
from rapidy import web

class Handler(web.View):
    async def get(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def post(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def put(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def patch(self) -> web.Response:
        return web.json_response({'data': 'success'})

    async def delete(self) -> web.Response:
        return web.json_response({'data': 'success'})

app = web.Application()
app.add_routes(
    [
        web.get('/', Handler),
        web.post('/', Handler),
        web.put('/', Handler),
        web.patch('/', Handler),
        web.delete('/', Handler),
    ]
)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```
</details>

## Middleware

!!! info "Примечание"
    В middleware обработчике
    <b><span class="note-color">первым аргументом</span></b>
    всегда должен быть <span class="note-color">web.Request</span>, а вторым <span class="note-color">handler</span>.

```Python hl_lines="5 15"
from rapidy import web
from rapidy.typedefs import HandlerType

@web.middleware
async def hello_middleware(
        request: web.Request,
        handler: HandlerType,
) -> web.StreamResponse:
    request['data'] = {'hello': 'world'}
    return await handler(request)

async def handler(request: web.Request) -> web.Response:
    return web.json_response(request['data'])

app = web.Application(middlewares=[hello_middleware])
app.add_routes([web.get('/', handler)])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

## Пример простой валидации

```Python hl_lines="10 17 18"
from rapidy import web
from rapidy.request_params import Header, JsonBody
from rapidy.typedefs import HandlerType
from typing_extensions import Annotated

@web.middleware
async def hello_middleware(
        request: web.Request,
        handler: HandlerType,
        bearer_token: Annotated[str, Header(alias='Authorization')] = 'Bearer ...',
) -> web.StreamResponse:
    request['token'] = bearer_token
    return await handler(request)

async def handler(
        request: web.Request,
        host: Annotated[str, Header(alias='Host')],
        username: Annotated[str, JsonBody],
) -> web.Response:
    example_data = {'token': request['token'], 'host': host, 'username': username}
    return web.json_response(example_data)

app = web.Application(middlewares=[hello_middleware])
app.add_routes([web.post('/', handler)])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

!!! tip "Совет"
    **Больше примеров валидации [Examples](examples.md)**

## Запуск веб-сервера
Скопируйте код на шаге выше в `main.py`.

```bash
python3 main.py
```
