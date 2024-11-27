from typing import Any

import pytest
from pydantic import BaseModel, Field

from rapidy.encoders import jsonify


class InnerData(BaseModel):
    test: str = Field('test', alias='Test')


class Data(BaseModel):
    test: str = Field('test', alias='Test')
    another_test: str = Field('another_test', alias='AnotherTest')
    another_inner_test: InnerData = Field(default_factory=InnerData, alias='AnotherInnerTest')


@pytest.mark.parametrize(
    'include_fields, expected_data',
    [
        [{'test'}, {'Test': 'test'}],
        [
            {'another_test', 'test', 'another_inner_test'},
            {'AnotherTest': 'another_test', 'Test': 'test', 'AnotherInnerTest': {'Test': 'test'}},
        ],
        [{}, {}],
    ],
)
def test_include_by_alias(include_fields: Any, expected_data: Any) -> None:
    assert jsonify(Data(), include=include_fields) == expected_data


@pytest.mark.parametrize(
    'exclude_fields, expected_data',
    [
        [{'test'}, {'AnotherTest': 'another_test', 'AnotherInnerTest': {'Test': 'test'}}],
        [{'another_test': True, 'test': True, 'another_inner_test': {'test'}}, {'AnotherInnerTest': {}}],
        [{'another_test', 'test', 'another_inner_test'}, {}],
        [{}, {'Test': 'test', 'AnotherTest': 'another_test', 'AnotherInnerTest': {'Test': 'test'}}],
    ],
)
def test_exclude_by_alias(exclude_fields: Any, expected_data: Any) -> None:
    assert jsonify(Data(), exclude=exclude_fields) == expected_data
