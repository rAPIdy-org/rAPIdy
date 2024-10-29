from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Final, Optional

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel, ConfigDict, Field

from rapidy import web
from rapidy._constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy.encoders import Exclude, Include
from rapidy.enums import ContentType, HeaderName

PATH: Final[str] = '/'


class TestEnum(Enum):
    test = 'test'


@dataclass
class DataclassTest:
    test: str = 'test'


class BaseModelTest(BaseModel):
    test: str = Field('test', alias='Test')
    test_none: None = None

    if PYDANTIC_V1:
        class Config:
            allow_population_by_field_name = True,

    elif PYDANTIC_V2:
        model_config: ConfigDict = ConfigDict(populate_by_name=True)

    else:
        raise ValueError


class ExtractMethod(str, Enum):
    text = 'text'
    read = 'read'
    json = 'json'


@dataclass
class TestCase:
    id: str
    response_body: Any = 'test'
    response_content_type: Optional[ContentType] = None
    expected_data: Any = 'test'
    extract_method: ExtractMethod = ExtractMethod.text
    expected_content_type: str = 'text/plain; charset=utf-8'

    include: Optional[Include] = None
    exclude: Optional[Exclude] = None
    by_alias: bool = True
    exclude_unset: bool = False
    exclude_defaults: bool = False
    exclude_none: bool = False

    __test__ = False


@dataclass
class TestCaseTextPlain(TestCase):
    response_content_type: ContentType = ContentType.text_plain


@dataclass
class TestCaseJson(TestCase):
    response_content_type: ContentType = ContentType.json
    extract_method: ExtractMethod = ExtractMethod.json
    expected_content_type: str = 'application/json; charset=utf-8'


test_cases = (
    # UNKNOWN CONTENT-TYPE
    TestCase(
        id='str-unknown',
    ),
    TestCase(
        id='enum-unknown',
        response_body=TestEnum.test,
    ),
    TestCase(
        id='int-unknown',
        response_body=1,
        expected_data='1',
    ),
    TestCase(
        id='float-unknown',
        response_body=1.0,
        expected_data='1.0',
    ),
    TestCase(
        id='decimal-unknown',
        response_body=Decimal('1.0'),
        expected_data='1.0',
    ),
    TestCase(
        id='bool-unknown',
        response_body=True,
        expected_data='true',
    ),
    TestCase(
        id='dict-unknown',
        response_body={'Test': 'test'},
        expected_data={'Test': 'test'},
        extract_method=ExtractMethod.json,
        expected_content_type='application/json; charset=utf-8',
    ),
    TestCase(
        id='base-model-unknown',
        response_body=BaseModelTest(),
        expected_data={'Test': 'test', 'test_none': None},
        extract_method=ExtractMethod.json,
        expected_content_type='application/json; charset=utf-8',
    ),
    TestCase(
        id='dataclass-unknown',
        response_body=DataclassTest(),
        expected_data={'test': 'test'},
        extract_method=ExtractMethod.json,
        expected_content_type='application/json; charset=utf-8',
    ),

    # CONTENT-TYPE text/plain
    TestCaseTextPlain(
        id='str-text-plain',
    ),
    TestCaseTextPlain(
        id='enum-text-plain',
        response_body=TestEnum.test,
    ),
    TestCaseTextPlain(
        id='int-text-plain',
        response_body=1,
        expected_data='1',
    ),
    TestCaseTextPlain(
        id='float-text-plain',
        response_body=1.0,
        expected_data='1.0',
    ),
    TestCaseTextPlain(
        id='decimal-text-plain',
        response_body=Decimal('1.0'),
        expected_data='1.0',
    ),
    TestCaseTextPlain(
        id='bool-text-plain',
        response_body=True,
        expected_data='true',
    ),
    TestCaseTextPlain(
        id='dict-text-plain',
        response_body={'Test': 'test'},
        expected_data='{"Test": "test"}',
    ),
    TestCaseTextPlain(
        id='base-model-text-plain',
        response_body=BaseModelTest(),
        expected_data='{"Test": "test", "test_none": null}',
    ),
    TestCaseTextPlain(
        id='dataclass-text-plain',
        response_body=DataclassTest(),
        expected_data='{"test": "test"}',
    ),

    # CONTENT-TYPE application/json
    TestCaseJson(
        id='str-json',
    ),
    TestCaseJson(
        id='enum-json',
        response_body=TestEnum.test,
    ),
    TestCaseJson(
        id='int-json',
        response_body=1,
        expected_data=1,
    ),
    TestCaseJson(
        id='float-json',
        response_body=1.0,
        expected_data=1.0,
    ),
    TestCaseJson(
        id='decimal-json',
        response_body=Decimal('1.0'),
        expected_data='1.0',
    ),
    TestCaseJson(
        id='bool-json',
        response_body=True,
        expected_data=True,
    ),
    TestCaseJson(
        id='base-model-json',
        response_body=BaseModelTest(),
        expected_data={'Test': 'test', 'test_none': None},
    ),
    TestCaseJson(
        id='dataclass-json',
        response_body=DataclassTest(),
        expected_data={'test': 'test'},
    ),

    # include
    TestCaseJson(
        id='base-model-include',
        include={'test'},
        response_body=BaseModelTest(),
        expected_data={'Test': 'test'},
    ),

    # exclude
    TestCaseJson(
        id='base-model-exclude',
        exclude={'test'},
        response_body=BaseModelTest(),
        expected_data={'test_none': None},
    ),

    # by alias
    TestCaseJson(
        id='base-model-by-alias-true',
        by_alias=True,
        response_body=BaseModelTest(),
        expected_data={'Test': 'test', 'test_none': None},
    ),
    TestCaseJson(
        id='base-model-by-alias-false',
        by_alias=False,
        response_body=BaseModelTest(),
        expected_data={'test': 'test', 'test_none': None},
    ),

    # exclude_unset
    TestCaseJson(
        id='base-model-exclude-unset',
        exclude_unset=True,
        response_body=BaseModelTest(),
        expected_data={},
    ),

    # exclude_defaults
    TestCaseJson(
        id='base-model-exclude-defaults',
        exclude_defaults=True,
        response_body=BaseModelTest(),
        expected_data={},
    ),

    # exclude_none
    TestCaseJson(
        id='base-model-exclude-none',
        exclude_none=True,
        response_body=BaseModelTest(),
        expected_data={'Test': 'test'},
    ),
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
async def test_response(aiohttp_client: AiohttpClient, test_case: TestCase) -> None:
    async def handler() -> web.Response:
        return web.Response(
            body=test_case.response_body,
            content_type=test_case.response_content_type,
            include=test_case.include,
            exclude=test_case.exclude,
            by_alias=test_case.by_alias,
            exclude_unset=test_case.exclude_unset,
            exclude_defaults=test_case.exclude_defaults,
            exclude_none=test_case.exclude_none,
        )

    app = web.Application()
    app.add_routes([web.get(PATH, handler)])

    client = await aiohttp_client(app)
    resp = await client.get(PATH)

    data = await getattr(resp, test_case.extract_method)()
    assert data == test_case.expected_data

    assert resp.headers.get(HeaderName.content_type) == test_case.expected_content_type
