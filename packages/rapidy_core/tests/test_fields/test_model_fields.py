import pytest
from rapidy_core.fields import (
    ABCRapidyModelField,
    ModelFieldCreationError,
    RapidyFieldInfo,
    RapidyModelField,
    create_model_field,
    create_model_field_by_annotation,
)
from rapidy_core.typedefs import Undefined


def _field_info(
    annotation: object, *, default: object = Undefined, alias: str | None = None
) -> RapidyFieldInfo:
    field_info = RapidyFieldInfo(default=default, alias=alias)
    field_info.annotation = annotation
    field_info.name = "x"
    return field_info


def test_create_model_field_builds_field() -> None:
    model_field = create_model_field(_field_info(int))
    assert isinstance(model_field, RapidyModelField)
    assert model_field.name == "x"
    assert model_field.alias == "x"
    assert model_field.required is True


def test_optional_annotation_not_required() -> None:
    assert create_model_field(_field_info(int | None)).required is False


def test_default_makes_not_required() -> None:
    model_field = create_model_field(_field_info(int, default=5))
    assert model_field.required is False
    assert model_field.default == 5
    assert model_field.get_default() == 5


def test_alias_from_field_info() -> None:
    assert create_model_field(_field_info(int, alias="X")).alias == "X"


def test_validate_ok_returns_value_and_none() -> None:
    model_field = create_model_field(_field_info(int))
    assert model_field.validate("7", {}, loc=("q",)) == (7, None)


def test_validate_error_prefixes_loc() -> None:
    result, errors = create_model_field(_field_info(int)).validate(
        "abc", {}, loc=("q",)
    )
    assert result is None
    assert errors is not None
    assert errors[0]["loc"][0] == "q"


def test_create_model_field_by_annotation() -> None:
    model_field = create_model_field_by_annotation(int)
    assert model_field.name == "data"
    assert model_field.required is True


def test_creation_error_wraps_cause_and_names_type() -> None:
    class _NoSchema:
        pass

    with pytest.raises(ModelFieldCreationError) as exc_info:
        create_model_field_by_annotation(_NoSchema)
    assert exc_info.value.__cause__ is not None
    assert str(_NoSchema) in str(exc_info.value)


def test_abc_model_field_is_abstract() -> None:
    with pytest.raises(TypeError):
        ABCRapidyModelField(name="x", field_info=RapidyFieldInfo())  # type: ignore[abstract]
