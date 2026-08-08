from typing import Annotated

import pytest
from annotated_types import Gt
from pydantic.fields import FieldInfo
from rapidy_core.fields import RapidyFieldInfo, copy_field_info


def test_rapidy_field_info_is_pydantic_field_info() -> None:
    field_info = RapidyFieldInfo()
    assert isinstance(field_info, FieldInfo)
    assert field_info.can_default is True


def test_unset_fields_not_forwarded_to_pydantic() -> None:
    assert RapidyFieldInfo().alias is None


def test_alias_forwarded() -> None:
    assert RapidyFieldInfo(alias="X").alias == "X"


def test_need_validate_flag() -> None:
    assert RapidyFieldInfo().need_validate is True
    assert RapidyFieldInfo(validate=False).need_validate is False


def test_numeric_constraints_applied() -> None:
    field_info = RapidyFieldInfo(gt=1, le=10)
    assert any(getattr(item, "gt", None) == 1 for item in field_info.metadata)
    assert any(getattr(item, "le", None) == 10 for item in field_info.metadata)


def test_deprecated_forwarded() -> None:
    assert RapidyFieldInfo(deprecated=True).deprecated is True


def test_regex_extra_emits_deprecation_and_maps_to_pattern() -> None:
    with pytest.warns(DeprecationWarning):
        field_info = RapidyFieldInfo(regex="^a$")
    assert any(getattr(item, "pattern", None) == "^a$" for item in field_info.metadata)


def test_pattern_wins_over_regex() -> None:
    field_info = RapidyFieldInfo(pattern="^p$", regex="^r$")
    assert any(getattr(item, "pattern", None) == "^p$" for item in field_info.metadata)


def test_copy_field_info_returns_independent_copy() -> None:
    field_info = RapidyFieldInfo(alias="X")
    copied = copy_field_info(field_info=field_info, annotation=int)
    assert copied is not field_info
    assert copied.alias == "X"


def test_copy_field_info_merges_annotated_metadata() -> None:
    copied = copy_field_info(
        field_info=RapidyFieldInfo(), annotation=Annotated[int, Gt(0)]
    )
    assert copied.annotation is int
    assert any(isinstance(item, Gt) for item in copied.metadata)
