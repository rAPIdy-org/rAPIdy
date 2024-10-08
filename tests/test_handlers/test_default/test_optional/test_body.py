import pytest
from aiohttp import StreamReader
from aiohttp.pytest_plugin import AiohttpClient

from rapidy.enums import RequestBodyType
from tests.test_handlers.test_default.base import body_test_cases, BodyTestCase
from tests.test_handlers.test_default.test_optional.base import (
    base_test_optional,
    base_test_optional_schema_param_fields,
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in body_test_cases])
async def test_optional(aiohttp_client: AiohttpClient, test_case: BodyTestCase) -> None:
    await base_test_optional(
        aiohttp_client,
        annotation=test_case.annotation,
        type_=test_case.param_type,
        body_type=test_case.body_type,
        can_default=test_case.annotation != StreamReader,
        check_content_type=False,  # only for tests
    )


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in body_test_cases])
async def test_optional_schema_param_fields(aiohttp_client: AiohttpClient, test_case: BodyTestCase) -> None:
    if test_case.body_type in (RequestBodyType.text, RequestBodyType.binary):
        return

    await base_test_optional_schema_param_fields(
        aiohttp_client,
        type_=test_case.param_type,
        body_type=test_case.body_type,
        request_kwargs=test_case.request_kwargs,
        check_content_type=False,  # only for tests
    )
