from http import HTTPStatus
from typing import Any

import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web


async def handler_request_fst(  # type: ignore[no-untyped-def]
    r,
    any_param=web.Headers(),
) -> None:
    pass


async def handler_request_snd(  # type: ignore[no-untyped-def]
    any_param=web.Headers(),
    r: web.Request = ...,
) -> None:
    pass


@pytest.mark.parametrize('handler', (handler_request_fst, handler_request_snd))
async def test_param_annotation_empty(aiohttp_client: AiohttpClient, handler: Any) -> None:
    app = web.Application()
    app.add_routes([web.get('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.get('/')

    assert resp.status == HTTPStatus.OK
