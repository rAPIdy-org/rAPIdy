import pytest
from pytest_aiohttp.plugin import AiohttpClient

from tests.test_http.test_server.test_param_attrs.helpers import base_test, create_test_cases, TestCase

strict_true_test_cases = create_test_cases(1, '2s', skip_only_str_params=True)
strict_false_test_cases = create_test_cases('1')


@pytest.mark.parametrize(
    'test_case', [
        pytest.param(test_case, id=test_case.id) for test_case in strict_true_test_cases
    ],
)
async def test_strict_fields_strict(
        aiohttp_client: AiohttpClient,
        test_case: TestCase,
) -> None:
    await base_test(
        aiohttp_client=aiohttp_client,
        annotation=int,
        param=test_case.param(strict=True),
        test_case=test_case,
    )


@pytest.mark.parametrize(
    'test_case', [
        pytest.param(test_case, id=test_case.id) for test_case in strict_false_test_cases
    ],
)
async def test_strict_fields_no_strict(
        aiohttp_client: AiohttpClient,
        test_case: TestCase,
) -> None:
    await base_test(
        aiohttp_client=aiohttp_client,
        annotation=int,
        param=test_case.param(strict=False),
        test_case=test_case,
    )
