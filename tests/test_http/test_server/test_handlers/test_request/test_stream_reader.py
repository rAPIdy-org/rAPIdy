from http import HTTPStatus

from aiohttp.pytest_plugin import AiohttpClient

from rapidy import StreamReader, web


async def test_success(aiohttp_client: AiohttpClient) -> None:
    async def handler(body: StreamReader = web.Body(content_type='text/*')) -> None:
        assert await body.read() == b'data'

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post('/', data='data')

    assert resp.status == HTTPStatus.OK, await resp.text()
