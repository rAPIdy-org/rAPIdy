from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Final, Optional

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel, ConfigDict, Field

from rapidy import Rapidy, web
from rapidy.constants import PYDANTIC_IS_V1
from rapidy.encoders import Exclude, Include
from rapidy.enums import ContentType, HeaderName
from rapidy.http import Response
from rapidy.web_response import ResponseDuplicateBodyError
from tests.constants import ClientBodyExtractMethod

PATH: Final[str] = '/'
JSON_CHARSET_UTF8: Final[str] = 'application/json; charset=utf-8'


class TestEnum(Enum):
    test = 'test'


@dataclass
class DataclassTest:
    test: str = 'test'


class BaseModelTest(BaseModel):
    test: str = Field('test', alias='Test')
    test_none: None = None

    if PYDANTIC_IS_V1:

        class Config:
            allow_population_by_field_name = True

    else:
        model_config: ConfigDict = ConfigDict(populate_by_name=True)


class BodySetterName(str, Enum):
    body = 'body'
    text = 'text'


@dataclass
class TestCase:
    id: str
    response_body: Any = 'test'
    response_content_type: Optional[ContentType] = None
    expected_data: Any = 'test'
    extract_method: ClientBodyExtractMethod = ClientBodyExtractMethod.text
    expected_content_type: str = 'text/plain; charset=utf-8'

    setter: BodySetterName = BodySetterName.body

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
    extract_method: ClientBodyExtractMethod = ClientBodyExtractMethod.json
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
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='base-model-unknown',
        response_body=BaseModelTest(),
        expected_data={'Test': 'test', 'test_none': None},
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='dataclass-unknown',
        response_body=DataclassTest(),
        expected_data={'test': 'test'},
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='tuple-unknown',
        response_body=('test', 'test'),
        expected_data=['test', 'test'],
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='list-unknown',
        response_body=['test', 'test'],
        expected_data=['test', 'test'],
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='set-unknown',
        response_body={'test'},
        expected_data=['test'],
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='frozenset-unknown',
        response_body=frozenset(('test',)),
        expected_data=['test'],
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='default-dict-unknown',
        response_body=defaultdict(int),
        expected_data={},
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
    ),
    TestCase(
        id='counter-unknown',
        response_body=Counter(('test', 'test')),
        expected_data={'test': 2},
        extract_method=ClientBodyExtractMethod.json,
        expected_content_type=JSON_CHARSET_UTF8,
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
    TestCaseTextPlain(
        id='tuple-text-plain',
        response_body=('test', 'test'),
        expected_data='["test", "test"]',
    ),
    TestCaseTextPlain(
        id='list-text-plain',
        response_body=['test', 'test'],
        expected_data='["test", "test"]',
    ),
    TestCaseTextPlain(
        id='set-text-plain',
        response_body={'test'},
        expected_data='["test"]',
    ),
    TestCaseTextPlain(
        id='frozenset-text-plain',
        response_body=frozenset(('test',)),
        expected_data='["test"]',
    ),
    TestCaseTextPlain(
        id='default-dict-text-plain',
        response_body=defaultdict(int),
        expected_data='{}',
    ),
    TestCaseTextPlain(
        id='counter-text-plain',
        response_body=Counter(('test', 'test')),
        expected_data='{"test": 2}',
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
    TestCaseJson(
        id='tuple-json',
        response_body=('test', 'test'),
        expected_data=['test', 'test'],
    ),
    TestCaseJson(
        id='list-json',
        response_body=['test', 'test'],
        expected_data=['test', 'test'],
    ),
    TestCaseJson(
        id='set-json',
        response_body={'test'},
        expected_data=['test'],
    ),
    TestCaseJson(
        id='frozenset-json',
        response_body=frozenset(('test',)),
        expected_data=['test'],
    ),
    TestCaseJson(
        id='default-dict-json',
        response_body=defaultdict(int),
        expected_data={},
    ),
    TestCaseJson(
        id='counter-json',
        response_body=Counter(('test', 'test')),
        expected_data={'test': 2},
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
    # setters
    TestCaseTextPlain(
        id='text-setter-str',
        setter=BodySetterName.text,
    ),
    TestCaseJson(
        id='text-setter-base-model',
        setter=BodySetterName.text,
        response_body=BaseModelTest(),
        expected_data={'Test': 'test', 'test_none': None},
    ),
)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
async def test_response(aiohttp_client: AiohttpClient, test_case: TestCase) -> None:
    async def handler() -> Response:
        response_kw = {
            test_case.setter.value: test_case.response_body,
        }

        return Response(
            **response_kw,
            content_type=test_case.response_content_type,
            include=test_case.include,
            exclude=test_case.exclude,
            by_alias=test_case.by_alias,
            exclude_unset=test_case.exclude_unset,
            exclude_defaults=test_case.exclude_defaults,
            exclude_none=test_case.exclude_none,
        )

    rapidy = Rapidy()
    rapidy.add_routes([web.get(PATH, handler)])

    client = await aiohttp_client(rapidy)
    resp = await client.get(PATH)

    data = await getattr(resp, test_case.extract_method)()
    assert data == test_case.expected_data

    assert resp.headers.get(HeaderName.content_type) == test_case.expected_content_type


def test_init_body_and_text() -> None:
    with pytest.raises(ResponseDuplicateBodyError):
        Response(body='test', text='test')
