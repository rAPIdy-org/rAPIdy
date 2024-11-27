import pytest
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Final

from tests.test_http.test_server.test_param_attrs.helpers import base_test, create_test_cases, TestCase

ALIAS: Final[str] = 'Alias'

test_cases = create_test_cases(correct_value='', data_key=ALIAS)


@pytest.mark.parametrize(
    'test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases],
)
async def test_alias_fields(
        aiohttp_client: AiohttpClient,
        test_case: TestCase,
) -> None:
    await base_test(
        aiohttp_client=aiohttp_client,
        annotation=str,
        param=test_case.param(alias=ALIAS),
        test_case=test_case,
    )
