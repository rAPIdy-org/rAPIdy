from http import HTTPStatus

from aiohttp.test_utils import TestClient

from src.config import Config


async def test_hello(
    app_config: Config,
    rapidy_client: TestClient,
) -> None:
    response = await rapidy_client.get('/')

    assert response.status == HTTPStatus.OK

    json = await response.json()

    assert json
    assert json['app_name'] == app_config.app_name
