from http import HTTPStatus

import pytest

from rapidy import Rapidy
from rapidy.http import get, Response
from tests.ported.app_checkers import check_handlers_all_response_models
from tests.ported.client import AppClientFactory


@pytest.mark.parametrize('status_code', [201, 400, 500])
async def test_status_code(app_client: AppClientFactory, status_code: int) -> None:
    await check_handlers_all_response_models(
        app_client=app_client,
        status_code=status_code,
        expected_status_code=status_code,
    )


async def test_override_status(app_client: AppClientFactory) -> None:
    @get('/', status_code=HTTPStatus.CREATED)
    async def handler(response: Response) -> None:
        response.set_status(HTTPStatus.ACCEPTED)

    rapidy = Rapidy(http_route_handlers=[handler])
    client = await app_client(rapidy)
    resp = await client.get('/')

    assert resp.status == HTTPStatus.ACCEPTED
