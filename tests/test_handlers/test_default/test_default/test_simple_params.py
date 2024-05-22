import pytest
from aiohttp.pytest_plugin import AiohttpClient

from tests.test_handlers.test_default.base import params_test_cases, TestCase
from tests.test_handlers.test_default.test_default.base import (
    base_test_can_default,
    base_test_incorrect_define_default_annotated_def,
    base_test_specify_both_default_and_default_factory,
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in params_test_cases])
async def test_default(test_case: TestCase, *, aiohttp_client: AiohttpClient) -> None:
    await base_test_can_default(
        aiohttp_client,
        type_=test_case.param_type,
        can_default=test_case.param_type.can_default,
    )


# NOTE: Let's not stop the `dev-user` if he wants to set default = None to a non-optional type
@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in params_test_cases])
async def test_optional_default(test_case: TestCase, *, aiohttp_client: AiohttpClient) -> None:
    await base_test_can_default(
        aiohttp_client,
        type_=test_case.param_type,
        default=None,
        can_default=test_case.param_type.can_default,
    )


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in params_test_cases])
async def test_incorrect_define_default_annotated_def(test_case: TestCase) -> None:
    if not test_case.param_type.can_default:
        return

    await base_test_incorrect_define_default_annotated_def(test_case.param_type)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in params_test_cases])
async def test_specify_both_default_and_default_factory(test_case: TestCase) -> None:
    if not test_case.param_type.can_default:
        return

    await base_test_specify_both_default_and_default_factory(test_case.param_type)
