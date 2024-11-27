import pytest
from aiohttp.pytest_plugin import AiohttpClient

from tests.test_http.test_server.test_handlers.test_default.base import params_test_cases, TestCase
from tests.test_http.test_server.test_handlers.test_default.test_optional.base import (
    base_test_optional,
    base_test_optional_schema_param_fields,
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in params_test_cases])
async def test_optional(aiohttp_client: AiohttpClient, test_case: TestCase) -> None:
    await base_test_optional(
        aiohttp_client,
        type_=test_case.param_type,
        can_default=test_case.param_type.can_default,
    )


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in params_test_cases])
async def test_optional_schema_param_fields(aiohttp_client: AiohttpClient, test_case: TestCase) -> None:
    if test_case.param_type.extract_single:
        return

    await base_test_optional_schema_param_fields(aiohttp_client, type_=test_case.param_type)
