from __future__ import annotations

import inspect
from typing import Annotated, Any

import pytest
from rapidy_core.exceptions import RapidyException
from rapidy_core.parameters.http import PathParam, QueryParam
from rapidy_core.signature import (
    CannotBeOptionalError,
    DefaultDefineTwiceError,
    DefaultError,
    ParameterCannotUseDefaultError,
    ParameterCannotUseDefaultFactoryError,
    ParameterNotInstanceError,
    SpecifyBothDefaultAndDefaultFactoryError,
    SpecifyBothDefaultAndOptionalError,
    SpecifyBothDefaultFactoryAndOptionalError,
    get_default_definition_attr_default,
    get_signature_raw_info,
)
from rapidy_core.typedefs import Undefined


def test_default_form_extracts_marker_to_data_attrs() -> None:
    def endpoint(user_id: str = PathParam()) -> None:
        pass

    raw = get_signature_raw_info(endpoint)

    assert len(raw.data_attrs) == 1
    assert len(raw.attrs) == 0
    field_info = raw.data_attrs[0].field_info
    assert field_info.name == "user_id"
    assert field_info.annotation is str
    assert field_info.default is Undefined


def test_annotated_form_extracts_marker_to_data_attrs() -> None:
    def endpoint(user_id: Annotated[str, PathParam()]) -> None:
        pass

    raw = get_signature_raw_info(endpoint)

    assert len(raw.data_attrs) == 1
    assert len(raw.attrs) == 0
    field_info = raw.data_attrs[0].field_info
    assert field_info.name == "user_id"
    assert field_info.annotation is str
    assert field_info.default is Undefined


def test_equivalent_forms_produce_equal_field_info() -> None:
    def default_form(user_id: str = PathParam()) -> None:
        pass

    def annotated_form(user_id: Annotated[str, PathParam()]) -> None:
        pass

    default_field = get_signature_raw_info(default_form).data_attrs[0].field_info
    annotated_field = get_signature_raw_info(annotated_form).data_attrs[0].field_info

    assert default_field.name == annotated_field.name == "user_id"
    assert default_field.default is annotated_field.default is Undefined
    assert default_field.annotation is annotated_field.annotation is str


def test_plain_parameter_goes_to_attrs() -> None:
    def endpoint(value: int) -> None:
        pass

    raw = get_signature_raw_info(endpoint)

    assert len(raw.data_attrs) == 0
    assert len(raw.attrs) == 1
    assert raw.attrs[0].attribute_name == "value"
    assert raw.attrs[0].attribute_annotation is int


def test_return_annotation_captured() -> None:
    def endpoint() -> str:
        return "result"

    assert get_signature_raw_info(endpoint).return_annotation is str


def test_attribute_index_is_monotonic() -> None:
    def endpoint(first: int, second: str = QueryParam()) -> None:
        pass

    raw = get_signature_raw_info(endpoint)

    assert raw.attrs[0].attribute_idx == 0
    assert raw.data_attrs[0].attribute_idx == 1


def test_field_default_used_when_marker_has_default() -> None:
    def endpoint(query: str = QueryParam("hello")) -> None:
        pass

    field_info = get_signature_raw_info(endpoint).data_attrs[0].field_info
    assert field_info.default == "hello"


def test_optional_marker_default_becomes_none() -> None:
    def endpoint(query: str | None = QueryParam()) -> None:
        pass

    field_info = get_signature_raw_info(endpoint).data_attrs[0].field_info
    assert field_info.default is None


def test_default_form_optional_with_postponed_annotations() -> None:
    def endpoint(query: str | None = QueryParam()) -> None:
        pass

    field_info = get_signature_raw_info(endpoint).data_attrs[0].field_info

    assert field_info.default is None
    assert field_info.annotation == str | None


def test_plain_optional_parameter_goes_to_attrs_without_index_error() -> None:
    def endpoint(value: str | None) -> None:
        pass

    raw = get_signature_raw_info(endpoint)

    assert not raw.data_attrs
    assert raw.attrs[0].attribute_annotation == str | None


def test_annotated_param_default_used() -> None:
    def endpoint(query: Annotated[str, QueryParam()] = "world") -> None:
        pass

    field_info = get_signature_raw_info(endpoint).data_attrs[0].field_info
    assert field_info.default == "world"


def test_conflict_parameter_not_instance_default_form() -> None:
    def endpoint(value: str = PathParam) -> None:  # type: ignore[assignment]
        pass

    with pytest.raises(ParameterNotInstanceError):
        get_signature_raw_info(endpoint)


def test_conflict_parameter_not_instance_annotated_form() -> None:
    def endpoint(value: Annotated[str, PathParam]) -> None:
        pass

    with pytest.raises(ParameterNotInstanceError):
        get_signature_raw_info(endpoint)


def test_conflict_default_define_twice_annotated_form() -> None:
    def endpoint(
        value: Annotated[str, QueryParam("field")] = "parameter",
    ) -> None:
        pass

    with pytest.raises(DefaultDefineTwiceError):
        get_signature_raw_info(endpoint)


def test_conflict_path_param_cannot_use_default() -> None:
    def endpoint(value: str = PathParam("value")) -> None:
        pass

    with pytest.raises(ParameterCannotUseDefaultError):
        get_signature_raw_info(endpoint)


def test_conflict_path_param_cannot_be_optional() -> None:
    def endpoint(value: str | None = PathParam()) -> None:
        pass

    with pytest.raises(CannotBeOptionalError):
        get_signature_raw_info(endpoint)


def test_conflict_path_param_cannot_use_default_factory() -> None:
    def endpoint(
        value: list[Any] = PathParam(default_factory=list),  # noqa: B008
    ) -> None:
        pass

    with pytest.raises(ParameterCannotUseDefaultFactoryError):
        get_signature_raw_info(endpoint)


def test_conflict_specify_both_default_and_optional() -> None:
    def endpoint(value: str | None = QueryParam("value")) -> None:
        pass

    with pytest.raises(SpecifyBothDefaultAndOptionalError):
        get_signature_raw_info(endpoint)


def test_conflict_specify_both_default_factory_and_optional() -> None:
    def endpoint(
        value: list[Any] | None = QueryParam(default_factory=list),  # noqa: B008
    ) -> None:
        pass

    with pytest.raises(SpecifyBothDefaultFactoryAndOptionalError):
        get_signature_raw_info(endpoint)


def test_conflict_both_default_and_default_factory() -> None:
    # Pydantic normally rejects this during construction; mutate the field to
    # exercise the extraction layer's independent defensive check.
    field_info = QueryParam()
    field_info.default = "value"
    field_info.default_factory = list
    attribute = inspect.Parameter(
        "value",
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        annotation=str,
    )

    with pytest.raises(SpecifyBothDefaultAndDefaultFactoryError):
        get_default_definition_attr_default(
            field_info,
            func=lambda: None,
            attribute=attribute,
            type_annotation=str,
        )


def test_error_family_inherits_rapidy_exception() -> None:
    error_types = (
        DefaultError,
        ParameterNotInstanceError,
        ParameterCannotUseDefaultError,
        ParameterCannotUseDefaultFactoryError,
        SpecifyBothDefaultAndDefaultFactoryError,
        CannotBeOptionalError,
        SpecifyBothDefaultAndOptionalError,
        SpecifyBothDefaultFactoryAndOptionalError,
        DefaultDefineTwiceError,
    )

    assert all(issubclass(error_type, RapidyException) for error_type in error_types)
    assert not issubclass(ParameterNotInstanceError, DefaultError)
    assert inspect.isclass(DefaultError)
    assert hasattr(DefaultError, "__abstractmethods__")


def test_error_message_carries_callable_and_attr_name() -> None:
    def broken(value: str = PathParam("value")) -> None:
        pass

    with pytest.raises(ParameterCannotUseDefaultError) as error_info:
        get_signature_raw_info(broken)

    message = str(error_info.value)
    assert "broken" in message
    assert "value" in message
