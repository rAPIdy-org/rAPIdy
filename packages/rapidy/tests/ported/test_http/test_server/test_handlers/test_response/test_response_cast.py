from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import BaseModel

from tests.ported.app_checkers import check_handlers_all_response_models
from tests.ported.client import AppClientFactory
from tests.ported.constants import ClientBodyExtractMethod, DEFAULT_RETURN_VALUE

test_dict = {'test': DEFAULT_RETURN_VALUE}


class BaseModelTest(BaseModel):
    test: str = 'test'


@dataclass
class DataclassTest:
    test: str = 'test'


@pytest.mark.parametrize('schema', [DataclassTest, BaseModelTest])
async def test_cast_dict_to_schema(app_client: AppClientFactory, schema: Any) -> None:
    await check_handlers_all_response_models(
        app_client=app_client,
        client_response_body_attr_name=ClientBodyExtractMethod.json,
        # handler fabric attrs
        handler_return_type=schema,
        handler_return_value=test_dict,
        expected_return_value=test_dict,
    )
