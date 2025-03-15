import pytest
from aiohttp.pytest_plugin import AiohttpClient

from tests.test_http.test_server.test_handlers.test_request.test_param_attrs.helpers import (
    base_test,
    create_test_cases,
    TestCase,
)


@pytest.mark.parametrize(
    'test_case',
    [pytest.param(test_case, id=test_case.id) for test_case in create_test_cases(2, 0)],
)
async def test_gt_fields(
    aiohttp_client: AiohttpClient,
    test_case: TestCase,
) -> None:
    await base_test(
        aiohttp_client=aiohttp_client,
        annotation=int,
        param=test_case.param(gt=1),
        test_case=test_case,
    )
