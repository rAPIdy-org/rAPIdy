from http import HTTPStatus
from typing import Any

import pytest

from rapidy import Rapidy
from rapidy.http import get, Headers, Request
from tests.ported.client import AppClientFactory


async def handler_request_fst(  # type: ignore[no-untyped-def]
    r,
    any_param=Headers(),
) -> None:
    pass


async def handler_request_snd(  # type: ignore[no-untyped-def]
    any_param=Headers(),
    r: Request = ...,
) -> None:
    pass


@pytest.mark.parametrize('handler', (handler_request_fst, handler_request_snd))
async def test_param_annotation_empty(app_client: AppClientFactory, handler: Any) -> None:
    app = Rapidy(http_route_handlers=[get.reg('/', handler)])

    client = await app_client(app)
    resp = await client.get('/')

    assert resp.status == HTTPStatus.OK
