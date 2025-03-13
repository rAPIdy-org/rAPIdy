from dataclasses import dataclass
from typing import Any

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel

from tests.app_checkers import check_handlers_all_response_models
from tests.constants import ClientBodyExtractMethod, DEFAULT_RETURN_VALUE

test_dict = {'test': DEFAULT_RETURN_VALUE}


class TestBaseModel(BaseModel):
    test: str = 'test'


@dataclass
class TestDataclass:
    test: str = 'test'


@pytest.mark.parametrize('schema', [TestDataclass, TestBaseModel])
async def test_cast_dict_to_schema(aiohttp_client: AiohttpClient, schema: Any) -> None:
    await check_handlers_all_response_models(
        aiohttp_client=aiohttp_client,
        aiohttp_client_response_body_attr_name=ClientBodyExtractMethod.json,
        # handler fabric attrs
        handler_return_type=schema,
        handler_return_value=test_dict,
        expected_return_value=test_dict,
    )
