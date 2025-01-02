import pytest
from pytest_aiohttp.plugin import AiohttpClient

from tests.test_http.test_server.test_param_attrs.helpers import base_test, create_test_cases, TestCase


@pytest.mark.parametrize(
    'test_case',
    [pytest.param(test_case, id=test_case.id) for test_case in create_test_cases('s', 'ss')],
)
async def test_max_len_fields(
    aiohttp_client: AiohttpClient,
    test_case: TestCase,
) -> None:
    await base_test(
        aiohttp_client=aiohttp_client,
        annotation=str,
        param=test_case.param(max_length=1),
        test_case=test_case,
    )
