from __future__ import annotations

import inspect
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, NoReturn, get_args, get_type_hints

from rapidy_core.annotation_checkers import (
    get_base_annotations,
    is_annotated,
    is_empty,
    is_optional,
)
from rapidy_core.exceptions import RapidyException
from rapidy_core.fields.field_info import RapidyFieldInfo, copy_field_info
from rapidy_core.typedefs import Required, Undefined

__all__ = (  # noqa: RUF022 - preserve the extraction API's logical order
    "DefaultError",
    "ParameterNotInstanceError",
    "ParameterCannotUseDefaultError",
    "ParameterCannotUseDefaultFactoryError",
    "SpecifyBothDefaultAndDefaultFactoryError",
    "CannotBeOptionalError",
    "SpecifyBothDefaultAndOptionalError",
    "SpecifyBothDefaultFactoryAndOptionalError",
    "DefaultDefineTwiceError",
    "is_rapidy_type",
    "check_default_value_for_field_exists",
    "raise_if_field_cannot_default",
    "get_default_definition_attr_default",
    "get_annotated_definition_attr_default",
    "prepare_attribute_field_info",
    "create_data_attr",
    "get_signature_raw_info",
)


@dataclass(slots=True)
class _Attr:
    """Raw information about an ordinary callable parameter."""

    attribute_name: str
    attribute_idx: int
    attribute_annotation: Any


@dataclass(slots=True)
class _DataAttr(_Attr):
    """Raw information about a callable parameter carrying rAPIdy metadata."""

    field_info: RapidyFieldInfo


@dataclass(slots=True)
class _SignatureRawInfo:
    """Raw return and parameter information extracted from a callable."""

    return_annotation: Any
    attrs: list[_Attr] = field(default_factory=list)
    data_attrs: list[_DataAttr] = field(default_factory=list)


class DefaultError(RapidyException, ABC):
    """Base error class for signature default-related errors."""


class ParameterNotInstanceError(RapidyException):
    """Raised when a marker class is supplied instead of a marker instance."""

    message = "Rapidy parameter must be an instance."


class ParameterCannotUseDefaultError(DefaultError):
    """Raised when a marker does not permit a default value."""

    message = "`{class_name}` with type `{annotation}` cannot have a default value."


class ParameterCannotUseDefaultFactoryError(DefaultError):
    """Raised when a marker does not permit a default factory."""

    message = "`{class_name}` with type `{annotation}` cannot have a default_factory."


class SpecifyBothDefaultAndDefaultFactoryError(DefaultError):
    """Raised when both a default value and a factory are specified."""

    message = "`{class_name}` with type `{annotation}` cannot contain `default` and `default_factory` together."


class CannotBeOptionalError(DefaultError):
    """Raised when a marker does not permit an optional annotation."""

    message = "`{class_name}` with type `{annotation}` cannot be optional."


class SpecifyBothDefaultAndOptionalError(DefaultError):
    """Raised when an optional parameter also carries a non-None default."""

    message = "`{class_name}` with type `{annotation}` cannot be optional if it contains a default value."


class SpecifyBothDefaultFactoryAndOptionalError(DefaultError):
    """Raised when an optional parameter also carries a default factory."""

    message = "`{class_name}` with type `{annotation}` cannot be optional if it contains a default factory."


class DefaultDefineTwiceError(DefaultError):
    """Raised when defaults are supplied in both parts of an Annotated declaration."""

    message = "Cannot specify a default value using Param(<default_value>, ...) and `=` together."


def _callable_name(func: Callable[..., Any]) -> str:
    name = getattr(func, "__name__", None)
    return name if isinstance(name, str) else repr(func)


def _raise_signature_error(
    error_cls: type[RapidyException],
    *,
    func: Callable[..., Any],
    attr_name: str | None = None,
    class_name: str | None = None,
    annotation: Any = None,
) -> NoReturn:
    message = error_cls.message
    if class_name is not None:
        message = message.format(class_name=class_name, annotation=annotation)
    message = f"{message}\nCallable name: `{_callable_name(func)}`"
    if attr_name is not None:
        message = f"{message}\nAttribute name: `{attr_name}`"
    raise error_cls(message)


def is_rapidy_type(type_: Any) -> bool:
    """Return whether an object is a rAPIdy field-info class."""
    try:
        return isinstance(type_, type) and issubclass(type_, RapidyFieldInfo)
    except Exception:  # noqa: BLE001 - defensive predicate for arbitrary annotations
        return False


def check_default_value_for_field_exists(field_info: RapidyFieldInfo) -> bool:
    """Return whether field metadata carries an explicit default value."""
    return not (field_info.default is Undefined or field_info.default is Required)


def raise_if_field_cannot_default(
    field_info: RapidyFieldInfo,
    *,
    default_exists: bool,
    default_is_none: bool,
    param_is_optional: bool,
    func: Callable[..., Any],
    attribute: inspect.Parameter,
) -> None:
    """Validate default and optional combinations for a prepared marker."""
    error_context = {
        "func": func,
        "attr_name": attribute.name,
        "class_name": field_info.__class__.__name__,
        "annotation": attribute.annotation,
    }

    if not field_info.can_default and param_is_optional:
        _raise_signature_error(CannotBeOptionalError, **error_context)

    if default_exists and not field_info.can_default:
        _raise_signature_error(ParameterCannotUseDefaultError, **error_context)

    default_factory_exists = field_info.default_factory is not None

    if default_factory_exists and not field_info.can_default:
        _raise_signature_error(ParameterCannotUseDefaultFactoryError, **error_context)

    # Pydantic raises this earlier in most, but not all, construction paths.
    if default_exists and default_factory_exists:
        _raise_signature_error(
            SpecifyBothDefaultAndDefaultFactoryError,
            **error_context,
        )

    if default_exists and not default_is_none and param_is_optional:
        _raise_signature_error(SpecifyBothDefaultAndOptionalError, **error_context)

    if default_factory_exists and param_is_optional:
        _raise_signature_error(
            SpecifyBothDefaultFactoryAndOptionalError,
            **error_context,
        )


def get_default_definition_attr_default(
    field_info: RapidyFieldInfo,
    func: Callable[..., Any],
    attribute: inspect.Parameter,
    type_annotation: Any,
) -> Any:
    """Resolve a default for the ``x: T = Marker()`` declaration form."""
    param_is_optional = is_optional(type_annotation)

    raise_if_field_cannot_default(
        field_info,
        default_exists=check_default_value_for_field_exists(field_info),
        default_is_none=field_info.default is None,
        param_is_optional=param_is_optional,
        func=func,
        attribute=attribute,
    )

    if param_is_optional:
        return None

    return field_info.default


def get_annotated_definition_attr_default(
    attribute: inspect.Parameter,
    type_annotation: Any,
    field_info: RapidyFieldInfo,
    func: Callable[..., Any],
) -> Any:
    """Resolve a default for the ``Annotated[T, Marker()]`` declaration form."""
    default_value_for_param_exists = not is_empty(attribute.default)
    default_value_for_field_exists = check_default_value_for_field_exists(field_info)
    param_is_optional = is_optional(type_annotation)

    default: Any = Undefined
    if default_value_for_param_exists:
        default = attribute.default
    elif default_value_for_field_exists:
        default = field_info.default
    elif param_is_optional:
        default = None

    raise_if_field_cannot_default(
        field_info,
        default_exists=default_value_for_param_exists or default_value_for_field_exists,
        default_is_none=default is None,
        param_is_optional=param_is_optional,
        attribute=attribute,
        func=func,
    )

    if default_value_for_param_exists and default_value_for_field_exists:
        _raise_signature_error(
            DefaultDefineTwiceError,
            func=func,
            attr_name=attribute.name,
        )

    return default


def prepare_attribute_field_info(
    attribute: inspect.Parameter,
    type_annotation: Any,
    field_info: RapidyFieldInfo,
    annotation_def_as_annotated: bool,
    func: Callable[..., Any],
) -> RapidyFieldInfo:
    """Copy and prepare marker metadata for one callable parameter."""
    field_info = copy_field_info(field_info=field_info, annotation=type_annotation)
    if annotation_def_as_annotated:
        prepared_default = get_annotated_definition_attr_default(
            attribute=attribute,
            type_annotation=type_annotation,
            field_info=field_info,
            func=func,
        )
    else:
        prepared_default = get_default_definition_attr_default(
            attribute=attribute,
            field_info=field_info,
            func=func,
            type_annotation=type_annotation,
        )

    field_info.default = prepared_default
    field_info.name = attribute.name
    field_info.annotation = type_annotation if not is_empty(type_annotation) else Any

    return field_info


def create_data_attr(
    attribute: inspect.Parameter,
    attribute_idx: int,
    type_annotation: Any,
    raw_field_info: RapidyFieldInfo,
    annotation_def_as_annotated: bool,
    func: Callable[..., Any],
) -> _DataAttr:
    """Create a data-attribute container from raw marker metadata."""
    prepared_field_info = prepare_attribute_field_info(
        attribute=attribute,
        type_annotation=type_annotation,
        field_info=raw_field_info,
        annotation_def_as_annotated=annotation_def_as_annotated,
        func=func,
    )
    return _DataAttr(
        attribute_name=attribute.name,
        attribute_idx=attribute_idx,
        attribute_annotation=attribute.annotation,
        field_info=prepared_field_info,
    )


def get_signature_raw_info(func: Callable[..., Any]) -> _SignatureRawInfo:
    """Extract return, ordinary-parameter, and marker-parameter information."""
    hints = get_type_hints(func, include_extras=True)
    signature = inspect.signature(func)
    return_annotation = hints.get("return", signature.return_annotation)
    raw_info = _SignatureRawInfo(return_annotation=return_annotation)

    for attribute_idx, (param_name, parameter) in enumerate(
        signature.parameters.items()
    ):
        annotation = hints.get(param_name, parameter.annotation)

        if not is_empty(parameter.default):
            if isinstance(parameter.default, RapidyFieldInfo):
                raw_info.data_attrs.append(
                    create_data_attr(
                        attribute=parameter,
                        attribute_idx=attribute_idx,
                        type_annotation=annotation,
                        raw_field_info=parameter.default,
                        annotation_def_as_annotated=False,
                        func=func,
                    )
                )
                continue

            if is_rapidy_type(parameter.default):
                _raise_signature_error(
                    ParameterNotInstanceError,
                    func=func,
                    attr_name=param_name,
                )

        marker_annotation = annotation
        if is_optional(marker_annotation):
            base_annotations = get_base_annotations(marker_annotation)
            if base_annotations and is_annotated(base_annotations[0]):
                marker_annotation = base_annotations[0]

        if is_annotated(marker_annotation):
            annotated_args = get_args(marker_annotation)
            type_annotation = annotated_args[0]
            last_attr = annotated_args[-1]

            if isinstance(last_attr, RapidyFieldInfo):
                raw_info.data_attrs.append(
                    create_data_attr(
                        attribute=parameter,
                        attribute_idx=attribute_idx,
                        type_annotation=type_annotation,
                        raw_field_info=last_attr,
                        annotation_def_as_annotated=True,
                        func=func,
                    )
                )
                continue

            if is_rapidy_type(last_attr):
                _raise_signature_error(
                    ParameterNotInstanceError,
                    func=func,
                    attr_name=param_name,
                )

        raw_info.attrs.append(
            _Attr(
                attribute_name=parameter.name,
                attribute_idx=attribute_idx,
                attribute_annotation=annotation,
            )
        )

    return raw_info
