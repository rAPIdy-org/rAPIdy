from __future__ import annotations

import inspect
from abc import ABC
from typing import Any, get_type_hints, List
from typing_extensions import get_args

from attrs import define, Factory

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.annotation_checkers import get_base_annotations, is_annotated, is_empty, is_optional
from rapidy.endpoint_handlers.attr_containers import Attr, DataAttr
from rapidy.fields.field_info import copy_field_info, RapidyFieldInfo
from rapidy.routing.http.helper_types import HandlerPartial
from rapidy.typedefs import Handler, Required, Undefined


class DefaultError(RapidyHandlerException, ABC):
    """Base error class for handler-related errors."""


class ParameterNotInstanceError(RapidyHandlerException):
    """Raised when a Rapidy parameter is not an instance."""

    message = 'Rapidy parameter must be an instance.'


class ParameterCannotUseDefaultError(DefaultError):
    """Raised when a parameter cannot have a default value."""

    message = '`{class_name}` with type `{annotation}` cannot have a default value.'


class ParameterCannotUseDefaultFactoryError(DefaultError):
    """Raised when a parameter cannot use a default factory."""

    message = '`{class_name}` with type `{annotation}` cannot have a default_factory.'


class SpecifyBothDefaultAndDefaultFactoryError(DefaultError):
    """Raised when both default value and default factory are specified."""

    message = '`{class_name}` with type `{annotation}` cannot contain `default` and `default_factory` together.'


class CannotBeOptionalError(DefaultError):
    """Raised when a parameter cannot be optional."""

    message = '`{class_name}` with type `{annotation}` cannot be optional.'


class SpecifyBothDefaultAndOptionalError(DefaultError):
    """Raised when a parameter cannot be both optional and have a default value."""

    message = '`{class_name}` with type `{annotation}` cannot be optional if it contains a default value.'


class SpecifyBothDefaultFactoryAndOptionalError(DefaultError):
    """Raised when a parameter cannot be both optional and have a default factory."""

    message = '`{class_name}` with type `{annotation}` cannot be optional if it contains a default factory.'


class DefaultDefineTwiceError(DefaultError):
    """Raised when a default value is defined twice."""

    message = 'Cannot specify a default value using Param(<default_value>, ...) and `=` together.'


def create_data_attr(
    attribute: inspect.Parameter,
    attribute_idx: int,
    type_annotation: Any,
    raw_field_info: RapidyFieldInfo,
    annotation_def_as_annotated: bool,  # noqa: FBT001
    # only to create context with exception
    handler: Handler,
) -> DataAttr:
    """Creates a DataAttr instance based on the provided attribute and field information.

    Args:
        attribute (inspect.Parameter): The attribute to create the data attribute from.
        attribute_idx (int): The index of the attribute in the handler's signature.
        type_annotation (Any): The type annotation of the attribute.
        raw_field_info (RapidyFieldInfo): The raw field information for the attribute.
        annotation_def_as_annotated (bool): Flag indicating if the annotation is defined as annotated.
        handler (Handler): The handler to associate with the attribute.

    Returns:
        DataAttr: The created DataAttr instance.
    """
    prepared_field_info = prepare_attribute_field_info(
        attribute=attribute,
        type_annotation=type_annotation,
        field_info=raw_field_info,
        annotation_def_as_annotated=annotation_def_as_annotated,
        # only to create context with exception
        handler=handler,
    )
    return DataAttr(
        attribute_name=attribute.name,
        attribute_idx=attribute_idx,
        attribute_annotation=attribute.annotation,
        field_info=prepared_field_info,
    )


def check_default_value_for_field_exists(field_info: RapidyFieldInfo) -> bool:
    """Checks if a default value exists for a field.

    Args:
        field_info (RapidyFieldInfo): The field information to check.

    Returns:
        bool: True if a default value exists, otherwise False.
    """
    return not (field_info.default is Undefined or field_info.default is Required)


def raise_if_field_cannot_default(
    field_info: RapidyFieldInfo,
    *,
    default_exists: bool,
    default_is_none: bool,
    param_is_optional: bool,
    # only to create context with exception
    handler: Handler,
    attribute: inspect.Parameter,
) -> None:
    """Raises an error if a field cannot have a default value based on its configuration.

    Args:
        field_info (RapidyFieldInfo): The field information to check.
        default_exists (bool): Whether the field has a default value.
        default_is_none (bool): Whether the default value is None.
        param_is_optional (bool): Whether the parameter is optional.
        handler (Handler): The handler to associate with the error.
        attribute (inspect.Parameter): The attribute that caused the error.

    Raises:
        Various errors depending on the situation, such as `CannotBeOptionalError`,
        `ParameterCannotUseDefaultError`, etc.
    """
    if not field_info.can_default and param_is_optional:
        raise CannotBeOptionalError.create(
            annotation=attribute.annotation,
            class_name=field_info.__class__.__name__,
            handler=handler,
            attr_name=attribute.name,
        )

    if default_exists and not field_info.can_default:
        raise ParameterCannotUseDefaultError.create(
            annotation=attribute.annotation,
            class_name=field_info.__class__.__name__,
            handler=handler,
            attr_name=attribute.name,
        )

    default_factory_exists = field_info.default_factory is not None

    if default_factory_exists and not field_info.can_default:
        raise ParameterCannotUseDefaultFactoryError.create(
            annotation=attribute.annotation,
            class_name=field_info.__class__.__name__,
            handler=handler,
            attr_name=attribute.name,
        )

    # NOTE: This error is caused earlier by `pydantic` for some scenarios.
    if default_exists and default_factory_exists:
        raise SpecifyBothDefaultAndDefaultFactoryError.create(
            annotation=attribute.annotation,
            class_name=field_info.__class__.__name__,
            handler=handler,
            attr_name=attribute.name,
        )

    if default_exists and not default_is_none and param_is_optional:
        raise SpecifyBothDefaultAndOptionalError.create(
            annotation=attribute.annotation,
            class_name=field_info.__class__.__name__,
            handler=handler,
            attr_name=attribute.name,
        )

    if default_factory_exists and param_is_optional:
        raise SpecifyBothDefaultFactoryAndOptionalError.create(
            annotation=attribute.annotation,
            class_name=field_info.__class__.__name__,
            handler=handler,
            attr_name=attribute.name,
        )


def get_default_definition_attr_default(
    field_info: RapidyFieldInfo,
    # only to create context with exception
    handler: Handler,
    attribute: inspect.Parameter,
) -> Any:
    """Gets the default value for an attribute based on its field information and the handler.

    Args:
        field_info (RapidyFieldInfo): The field information.
        handler (Handler): The handler to associate with the default value.
        attribute (inspect.Parameter): The attribute to get the default value for.

    Returns:
        Any: The default value for the attribute.
    """
    param_is_optional = is_optional(attribute.annotation)

    raise_if_field_cannot_default(
        field_info,
        default_exists=check_default_value_for_field_exists(field_info),
        default_is_none=field_info.default is None,
        param_is_optional=param_is_optional,
        # only to create context with exception
        handler=handler,
        attribute=attribute,
    )

    if param_is_optional:
        return None

    return field_info.default


def get_annotated_definition_attr_default(
    attribute: inspect.Parameter,
    type_annotation: Any,
    field_info: RapidyFieldInfo,
    # only to create context with exception
    handler: Handler,
) -> Any:
    """Gets the default value for an annotated attribute.

    Args:
        attribute (inspect.Parameter): The attribute to get the default value for.
        type_annotation (Any): The type annotation for the attribute.
        field_info (RapidyFieldInfo): The field information for the attribute.
        handler (Handler): The handler to associate with the default value.

    Returns:
        Any: The default value for the attribute.
    """
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
        # only to create context with exception
        attribute=attribute,
        handler=handler,
    )

    if default_value_for_param_exists and default_value_for_field_exists:
        raise DefaultDefineTwiceError.create(handler=handler, attr_name=attribute.name)

    return default


def prepare_attribute_field_info(
    attribute: inspect.Parameter,
    type_annotation: Any,
    field_info: RapidyFieldInfo,
    annotation_def_as_annotated: bool,  # noqa: FBT001
    # only to create context with exception
    handler: Handler,
) -> RapidyFieldInfo:
    """Prepares field information for an attribute, including handling default values and annotations.

    Args:
        attribute (inspect.Parameter): The attribute to prepare the field info for.
        type_annotation (Any): The type annotation for the attribute.
        field_info (RapidyFieldInfo): The field information.
        annotation_def_as_annotated (bool): Whether the annotation is defined as annotated.
        handler (Handler): The handler to associate with the attribute.

    Returns:
        RapidyFieldInfo: The prepared field information.
    """
    field_info = copy_field_info(field_info=field_info, annotation=attribute.annotation)
    if annotation_def_as_annotated:
        prepared_default = get_annotated_definition_attr_default(
            attribute=attribute,
            type_annotation=type_annotation,
            field_info=field_info,
            # only to create context with exception
            handler=handler,
        )
    else:
        prepared_default = get_default_definition_attr_default(
            attribute=attribute,
            field_info=field_info,
            # only to create context with exception
            handler=handler,
        )

    field_info.default = prepared_default
    field_info.name = attribute.name
    field_info.annotation = type_annotation if not is_empty(type_annotation) else Any

    return field_info


def is_rapidy_type(type_: Any) -> bool:
    """Checks if a given type is a subclass of RapidyFieldInfo.

    Args:
        type_ (Any): The type to check.

    Returns:
        bool: True if the type is a subclass of RapidyFieldInfo, otherwise False.
    """
    try:
        return isinstance(type_, type) and issubclass(type_, RapidyFieldInfo)
    except Exception:  # noqa: BLE001
        return False


@define(slots=True)
class HandlerRawInfo:
    """Represents raw information about a handler's attributes.

    Attributes:
        return_annotation (Any): The return annotation of the handler.
        attrs (List[Attr]): A list of regular attributes for the handler.
        data_attrs (List[DataAttr]): A list of data attributes for the handler.
    """

    return_annotation: Any
    attrs: List[Attr] = Factory(list)
    data_attrs: List[DataAttr] = Factory(list)


def get_handler_raw_info(handler: Handler) -> HandlerRawInfo:  # noqa: C901
    """Gets the raw information about a handler's attributes and return annotation.

    Args:
        handler (Handler): The handler to retrieve the information for.

    Returns:
        HandlerRawInfo: The raw information about the handler's attributes.
    """
    try:
        hints = get_type_hints(handler, include_extras=True)
    except TypeError as get_hints_exc:
        if not isinstance(handler, HandlerPartial):  # FIXME: Remove after remove HandlerPartial
            raise get_hints_exc  # noqa: TRY201

        hints = get_type_hints(handler.handler, include_extras=True)

    sig = inspect.signature(handler)

    return_annotation = hints.get('return', sig.return_annotation)

    handler_raw_info = HandlerRawInfo(return_annotation=return_annotation)

    attribute_idx = -1
    for param_name, parameter in sig.parameters.items():
        attribute_idx += 1
        annotation = hints.get(param_name, parameter.annotation)

        if not is_empty(parameter.default):
            if isinstance(parameter.default, RapidyFieldInfo):
                data_attr = create_data_attr(
                    attribute=parameter,
                    attribute_idx=attribute_idx,
                    type_annotation=annotation,
                    raw_field_info=parameter.default,
                    annotation_def_as_annotated=False,
                    handler=handler,
                )
                handler_raw_info.data_attrs.append(data_attr)
                continue

            if is_rapidy_type(parameter.default):
                raise ParameterNotInstanceError.create(handler=handler, attr_name=param_name)

        if is_annotated(annotation) or is_optional(annotation):
            if is_optional(annotation):  # FIXME: double check
                base_annotations = get_base_annotations(annotation)
                if base_annotations:
                    annotation = base_annotations[0]

            annotated_args = get_args(annotation)
            type_annotation = annotated_args[0]
            last_attr = annotated_args[-1]

            if isinstance(last_attr, RapidyFieldInfo):
                data_attr = create_data_attr(
                    attribute=parameter,
                    attribute_idx=attribute_idx,
                    type_annotation=type_annotation,
                    raw_field_info=last_attr,
                    annotation_def_as_annotated=True,
                    handler=handler,
                )
                handler_raw_info.data_attrs.append(data_attr)
                continue

            if is_rapidy_type(last_attr):
                raise ParameterNotInstanceError.create(handler=handler, attr_name=param_name)

        attr = Attr(
            attribute_name=parameter.name,
            attribute_idx=attribute_idx,
            attribute_annotation=annotation,
        )

        handler_raw_info.attrs.append(attr)

    return handler_raw_info
