from collections import deque
from dataclasses import dataclass, field
from typing import Any, Final

import pytest
from pydantic import BaseModel, Field

from rapidy.encoders import jsonify
from rapidy.typedefs import DictStrAny

DEFAULT: Final[str] = 'test'
FIELD_NAME_BY_ALIAS: Final[str] = 'Test'
ATTR_NAME_BY_ALIAS: Final[str] = 'test_alias'
EXCLUDED_FIELD_NAME: Final[str] = 'test_exclude'


class _TestBaseModel(BaseModel):
    test_exclude: str
    test_default: str = Field(DEFAULT)
    test_alias: str = Field(alias=FIELD_NAME_BY_ALIAS)
    test_null: None


base_model_obj = _TestBaseModel(
    test_exclude=DEFAULT,
    Test=DEFAULT,
    test_null=None,
)


def create_expected_base_model_obj(
    *,
    include: Any = None,
    exclude: bool = False,
    by_alias: bool = True,
    exclude_unset_field: bool = False,
    exclude_default_field: bool = False,
    exclude_none_field: bool = False,
) -> DictStrAny:
    base_model_obj: DictStrAny = {}

    if include:
        base_model_obj['test_exclude'] = DEFAULT
        return base_model_obj

    if not exclude:
        base_model_obj['test_exclude'] = DEFAULT

    if by_alias:
        base_model_obj[FIELD_NAME_BY_ALIAS] = DEFAULT
    else:
        base_model_obj['test_alias'] = DEFAULT

    if not (exclude_unset_field or exclude_default_field):
        base_model_obj['test_default'] = DEFAULT

    if not exclude_none_field:
        base_model_obj['test_null'] = None

    return base_model_obj


@dataclass
class _TestDataclass:
    test_model: _TestBaseModel = field(default_factory=lambda: base_model_obj)


obj_to_prepare = {
    'test_list': [base_model_obj],
    'test_deque': deque([base_model_obj]),
    'test_dataclass': _TestDataclass(),
    'test_model': base_model_obj,
}


@pytest.mark.skip(reason='Encoder partially does not support nested BaseModel (fastapi legacy).')
def test_dict_include_nested_model() -> None:
    expected_obj = {'test_model': {EXCLUDED_FIELD_NAME}}
    assert jsonify(obj_to_prepare, include={'test_model': {EXCLUDED_FIELD_NAME}}) == expected_obj


@pytest.mark.skip(reason='Encoder partially does not support nested BaseModel (fastapi legacy).')
def test_dict_exclude_nested_model() -> None:
    expected_obj = create_expected_base_model_obj(exclude=True)
    assert jsonify(obj_to_prepare, exclude={'test_model': {EXCLUDED_FIELD_NAME}}) == expected_obj


@pytest.mark.skip(reason='Encoder partially does not support nested BaseModel (fastapi legacy).')
def test_dict_dataclass_include_nested_model() -> None:
    expected_obj = {'test_dataclass': {'test_model': {EXCLUDED_FIELD_NAME: DEFAULT}}}
    assert jsonify(obj_to_prepare, include={'test_model': {EXCLUDED_FIELD_NAME}}) == expected_obj


@pytest.mark.skip(reason='Encoder partially does not support nested BaseModel (fastapi legacy).')
def test_dict_dataclass_exclude_nested_model() -> None:
    expected_base_model_obj = create_expected_base_model_obj()
    expected_obj = {
        'test_list': [expected_base_model_obj],
        'test_dataclass': {
            'test_model': create_expected_base_model_obj(exclude=True),
        },
        'test_model': expected_base_model_obj,
    }
    assert (
        jsonify(
            obj_to_prepare,
            exclude={'test_dataclass': {'test_model': {EXCLUDED_FIELD_NAME}}},
        )
        == expected_obj
    )


@pytest.mark.parametrize('by_alias', [True, False])
def test_nested_by_alias(by_alias: bool) -> None:
    prepared_obj = jsonify(obj_to_prepare, by_alias=by_alias)

    dict_dataclass_test_model = prepared_obj['test_dataclass']['test_model']
    dict_test_model = prepared_obj['test_model']
    if by_alias:
        assert dict_dataclass_test_model.get(FIELD_NAME_BY_ALIAS)
        assert dict_test_model.get(FIELD_NAME_BY_ALIAS)
    else:
        assert dict_dataclass_test_model.get(ATTR_NAME_BY_ALIAS)
        assert dict_test_model.get(ATTR_NAME_BY_ALIAS)


def test_nested_exclude_default() -> None:
    expected_base_model_obj = create_expected_base_model_obj(exclude_default_field=True)
    expected_obj = {
        'test_list': [expected_base_model_obj],
        'test_deque': [expected_base_model_obj],
        'test_dataclass': {
            'test_model': expected_base_model_obj,
        },
        'test_model': expected_base_model_obj,
    }
    assert jsonify(obj_to_prepare, exclude_defaults=True) == expected_obj


def test_nested_model_exclude_none() -> None:
    expected_base_model_obj = create_expected_base_model_obj(exclude_none_field=True)
    expected_obj = {
        'test_list': [expected_base_model_obj],
        'test_deque': [expected_base_model_obj],
        'test_dataclass': {
            'test_model': expected_base_model_obj,
        },
        'test_model': expected_base_model_obj,
    }
    assert jsonify(obj_to_prepare, exclude_none=True) == expected_obj
