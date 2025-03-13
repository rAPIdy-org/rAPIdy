from aiohttp.pytest_plugin import AiohttpClient

from tests.app_checkers import check_handlers_all_response_models


async def test_status_code(aiohttp_client: AiohttpClient) -> None:
    await check_handlers_all_response_models(
        aiohttp_client=aiohttp_client,
    )
