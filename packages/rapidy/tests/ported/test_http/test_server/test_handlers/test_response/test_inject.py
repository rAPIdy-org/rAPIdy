from typing import Final

from rapidy_core.enums import ContentType, HeaderName

from rapidy import Rapidy
from rapidy.http import get, Response
from tests.ported.client import AppClientFactory
from tests.ported.constants import DEFAULT_RETURN_VALUE

PATH: Final[str] = '/'


async def test_injected_response(app_client: AppClientFactory) -> None:
    async def handler(response: Response) -> Response:
        response.text = DEFAULT_RETURN_VALUE
        return response

    rapidy = Rapidy(http_route_handlers=[get.reg(PATH, handler, response_content_type=ContentType.json)])

    client = await app_client(rapidy)
    resp = await client.get(PATH)

    assert await resp.text() == DEFAULT_RETURN_VALUE


async def test_update_data_for_injected_response(app_client: AppClientFactory) -> None:
    async def handler(response: Response) -> None:
        response.body = DEFAULT_RETURN_VALUE

    rapidy = Rapidy(http_route_handlers=[get.reg(PATH, handler, response_content_type=ContentType.json)])

    client = await app_client(rapidy)
    resp = await client.get(PATH)

    assert await resp.json() == DEFAULT_RETURN_VALUE


async def test_direct_response_ignore_pre_added_data(app_client: AppClientFactory) -> None:
    another_text_return_value: str = 'another_test_value'
    another_response_content_type: str = 'text/html'

    async def handler(response: Response) -> Response:
        response.text = DEFAULT_RETURN_VALUE
        return Response(
            body=another_text_return_value,
            headers={HeaderName.content_type: another_response_content_type},
        )

    rapidy = Rapidy(http_route_handlers=[get.reg(PATH, handler, response_content_type=ContentType.json)])

    client = await app_client(rapidy)
    resp = await client.get(PATH)

    assert await resp.text() == another_text_return_value
    assert resp.headers[HeaderName.content_type].startswith(another_response_content_type)
