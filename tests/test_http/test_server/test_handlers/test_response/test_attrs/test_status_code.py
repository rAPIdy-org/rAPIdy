from http import HTTPStatus

import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import Rapidy
from rapidy.http import get, Response
from tests.app_checkers import check_handlers_all_response_models


@pytest.mark.parametrize('status_code', [201, 400, 500])
async def test_status_code(aiohttp_client: AiohttpClient, status_code: int) -> None:
    await check_handlers_all_response_models(
        aiohttp_client=aiohttp_client,
        status_code=status_code,
        expected_status_code=status_code,
    )


async def test_override_status(aiohttp_client: AiohttpClient) -> None:
    @get('/', status_code=HTTPStatus.CREATED)
    async def handler(response: Response) -> None:
        response.set_status(HTTPStatus.ACCEPTED)

    rapidy = Rapidy(http_route_handlers=[handler])
    client = await aiohttp_client(rapidy)
    resp = await client.get('/')

    assert resp.status == HTTPStatus.ACCEPTED
