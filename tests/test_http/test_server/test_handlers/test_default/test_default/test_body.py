import pytest
from aiohttp import StreamReader
from aiohttp.pytest_plugin import AiohttpClient

from tests.test_http.test_server.test_handlers.test_default.base import body_test_cases, BodyTestCase
from tests.test_http.test_server.test_handlers.test_default.test_default.base import (
    base_test_can_default,
    base_test_incorrect_define_default_annotated_def,
    base_test_specify_both_default_and_default_factory,
)


def _body_type_can_default(test_case: BodyTestCase) -> bool:
    return test_case.annotation != StreamReader


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in body_test_cases])
async def test_default(test_case: BodyTestCase, *, aiohttp_client: AiohttpClient) -> None:
    await base_test_can_default(
        aiohttp_client,
        type_=test_case.param_type,
        annotation=test_case.annotation,
        can_default=_body_type_can_default(test_case),
        body_type=test_case.content_type,
        check_content_type=False,  # only for tests
    )


# NOTE: Let's not stop the `dev-user` if he wants to set default = None to a non-optional type
@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in body_test_cases])
async def test_optional_default(test_case: BodyTestCase, *, aiohttp_client: AiohttpClient) -> None:
    await base_test_can_default(
        aiohttp_client,
        type_=test_case.param_type,
        annotation=test_case.annotation,
        default=None,
        can_default=_body_type_can_default(test_case),
        body_type=test_case.content_type,
        check_content_type=False,  # only for tests
    )


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in body_test_cases])
async def test_incorrect_define_default_annotated_def(test_case: BodyTestCase) -> None:
    if not _body_type_can_default(test_case):
        return

    await base_test_incorrect_define_default_annotated_def(
        test_case.param_type,
        body_type=test_case.content_type,
        check_content_type=False,  # only for tests
    )


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in body_test_cases])
async def test_specify_both_default_and_default_factory(test_case: BodyTestCase) -> None:
    if not _body_type_can_default(test_case):
        return

    await base_test_specify_both_default_and_default_factory(test_case.param_type)
