from typing import Any, Final

import pytest
from pydantic import BaseModel, Field

from rapidy.encoders import jsonify
from rapidy.typedefs import DictStrAny

DEFAULT: Final[str] = 'test'
FIELD_NAME_BY_ALIAS: Final[str] = 'Test'
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


def test_model_include() -> None:
    expected_obj = create_expected_base_model_obj(include=True)
    assert jsonify(base_model_obj, include={EXCLUDED_FIELD_NAME}) == expected_obj


def test_model_exclude() -> None:
    expected_obj = create_expected_base_model_obj(exclude=True)
    assert jsonify(base_model_obj, exclude={EXCLUDED_FIELD_NAME}) == expected_obj


@pytest.mark.parametrize('override_default', [True, False])
def test_model_exclude_unset(override_default: bool) -> None:
    model = base_model_obj
    if override_default:
        model = _TestBaseModel(
            test_exclude=DEFAULT,
            Test=DEFAULT,
            test_null=None,
            test_default=DEFAULT,
        )
    expected_obj = create_expected_base_model_obj(exclude_unset_field=not override_default)
    assert jsonify(model, exclude_unset=True) == expected_obj


@pytest.mark.parametrize('by_alias', [True, False])
def test_model_by_alias(by_alias: bool) -> None:
    expected_obj = create_expected_base_model_obj(by_alias=by_alias)
    assert jsonify(base_model_obj, by_alias=by_alias) == expected_obj


def test_model_exclude_defaults() -> None:
    expected_obj = create_expected_base_model_obj(exclude_default_field=True)
    assert jsonify(base_model_obj, exclude_defaults=True) == expected_obj


def test_model_exclude_none() -> None:
    expected_obj = create_expected_base_model_obj(exclude_none_field=True)
    assert jsonify(base_model_obj, exclude_none=True) == expected_obj
