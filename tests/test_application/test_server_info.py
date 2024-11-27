import pytest
from pytest_aiohttp.plugin import AiohttpClient

from rapidy import web


@pytest.mark.parametrize('server_info_in_response', [True, False])
async def test_server_info(aiohttp_client: AiohttpClient, server_info_in_response: bool) -> None:
    app = web.Application(server_info_in_response=server_info_in_response)

    async def handler() -> None: pass

    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)

    resp = await client.post('/')
    assert resp.status == 200
    assert bool(resp.headers.get('Server')) == server_info_in_response
