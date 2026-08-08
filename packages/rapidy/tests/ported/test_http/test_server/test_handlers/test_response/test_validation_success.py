from tests.ported.app_checkers import check_handlers_all_response_models
from tests.ported.client import AppClientFactory


async def test_validation_success(app_client: AppClientFactory) -> None:
    await check_handlers_all_response_models(app_client=app_client)
