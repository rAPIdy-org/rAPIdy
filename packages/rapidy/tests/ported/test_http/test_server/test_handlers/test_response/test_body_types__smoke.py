from typing import Any

import pytest
from pydantic import BaseModel
from rapidy_core.enums import ContentType

from tests.ported.app_checkers import check_handlers_all_response_models
from tests.ported.client import AppClientFactory
from tests.ported.constants import ClientBodyExtractMethod, DEFAULT_RETURN_VALUE

test_dict = {'test': DEFAULT_RETURN_VALUE}


class TestCaseResponseBodyType(BaseModel):
    id: str

    handler_return_value: str = DEFAULT_RETURN_VALUE
    expected_return_value: Any = DEFAULT_RETURN_VALUE

    content_type: ContentType
    client_body_extract_method: ClientBodyExtractMethod = ClientBodyExtractMethod.json

    __test__ = False


test_body_types_cases = (
    # TODO: more body types  # noqa: FIX002
    TestCaseResponseBodyType(
        id='json',
        content_type=ContentType.json,
    ),
    TestCaseResponseBodyType(
        id='text',
        content_type=ContentType.text_plain,
        client_body_extract_method=ClientBodyExtractMethod.text,
    ),
    TestCaseResponseBodyType(
        id='binary',
        content_type=ContentType.stream,
        client_body_extract_method=ClientBodyExtractMethod.read,
        expected_return_value=DEFAULT_RETURN_VALUE.encode(),
    ),
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_body_types_cases])
async def test_body_types(app_client: AppClientFactory, test_case: TestCaseResponseBodyType) -> None:
    await check_handlers_all_response_models(
        app_client=app_client,
        # handler fabric attrs
        handler_return_value=test_case.handler_return_value,
        expected_return_value=test_case.expected_return_value,
        client_response_body_attr_name=test_case.client_body_extract_method,
        # handler attrs
        response_content_type=test_case.content_type,
    )
