from __future__ import annotations

import pytest

from rapidy import Rapidy
from rapidy.http import post
from tests.ported.client import AppClientFactory


@pytest.mark.parametrize('server_info_in_response', [True, False])
async def test_server_info(app_client: AppClientFactory, server_info_in_response: bool) -> None:
    async def handler() -> None:
        pass

    app = Rapidy(
        server_info_in_response=server_info_in_response,
        http_route_handlers=[post.reg('/', handler)],
    )
    client = await app_client(app)

    resp = await client.post('/')
    assert resp.status == 200
    assert bool(resp.headers.get('Server')) == server_info_in_response
