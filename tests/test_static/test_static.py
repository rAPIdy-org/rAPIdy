from http import HTTPStatus
from pathlib import Path
from typing import Any, Final

from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web
from rapidy.typedefs import CallNext

TEST_DIR: Final[Path] = Path(__file__).parent
FILE_DIR: Final[Path] = TEST_DIR / 'test.txt'


async def test_success_file_response(aiohttp_client: AiohttpClient) -> None:
    async def handler(request: web.Request) -> web.FileResponse:
        return web.FileResponse(FILE_DIR)

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post('/')

    assert resp.status == HTTPStatus.OK


async def test_success_static_response(aiohttp_client: AiohttpClient) -> None:
    app = web.Application()
    await _test_success_static_response(app=app, aiohttp_client=aiohttp_client)


async def test_success_static_response_with_middleware(aiohttp_client: AiohttpClient) -> None:
    @web.middleware
    async def middleware(request: web.Request, call_next: CallNext) -> web.StreamResponse:
        return await call_next(request)

    app = web.Application(middlewares=[middleware])
    await _test_success_static_response(app=app, aiohttp_client=aiohttp_client)


async def _test_success_static_response(app: web.Application, aiohttp_client: AiohttpClient) -> None:
    app.router.add_static(
        '/',
        path=TEST_DIR,
        append_version=True,  # очистка кеша
    )

    client = await aiohttp_client(app)
    resp = await client.get('/test.txt')

    assert resp.status == HTTPStatus.OK

    assert await resp.text() == 'test\n'
