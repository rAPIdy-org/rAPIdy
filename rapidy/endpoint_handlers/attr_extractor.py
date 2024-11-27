import inspect
from abc import ABC
from typing import Any, List

from attrs import define, Factory
from typing_extensions import get_args

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.annotation_checkers import is_annotated, is_empty, is_optional
from rapidy.endpoint_handlers.attr_containers import Attr, DataAttr
from rapidy.fields.field_info import copy_field_info, RapidyFieldInfo
from rapidy.typedefs import Handler, Required, Undefined


class DefaultError(RapidyHandlerException, ABC):
    """"""


class ParameterNotInstanceError(RapidyHandlerException):
    message = 'Rapidy parameter must be an instance.'


class ParameterCannotUseDefaultError(DefaultError):
    message = '`{class_name}` with type `{annotation}` cannot have a default value.'


class ParameterCannotUseDefaultFactoryError(DefaultError):
    message = '`{class_name}` with type `{annotation}` cannot have a default_factory.'


class SpecifyBothDefaultAndDefaultFactoryError(DefaultError):
    message = '`{class_name}` with type `{annotation}` cannot contain `default` and `default_factory` together.'


class CannotBeOptionalError(DefaultError):
    message = '`{class_name}` with type `{annotation}` cannot be optional.'


class SpecifyBothDefaultAndOptionalError(DefaultError):
    message = '`{class_name}` with type `{annotation}` cannot be optional if it contains a default value.'


class SpecifyBothDefaultFactoryAndOptionalError(DefaultError):
    message = '`{class_name}` with type `{annotation}` cannot be optional if it contains a default factory.'


class DefaultDefineTwiceError(DefaultError):
    message = 'Cannot specify a default value using Param(<default_value>, ...) and `=` together.'


def create_data_attr(
        attribute: inspect.Parameter,
        attribute_idx: int,
        type_annotation: Any,
        raw_field_info: RapidyFieldInfo,
        annotation_def_as_annotated: bool,
        # only to create context with exception
        handler: Handler,
) -> DataAttr:
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
        annotation_def_as_annotated: bool,
        # only to create context with exception
        handler: Handler,
) -> RapidyFieldInfo:
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
    field_info.annotation = type_annotation if not is_empty(type_annotation) else Any  # noqa: WPS504

    return field_info


def is_rapidy_type(type_: Any) -> bool:
    try:
        return isinstance(type_, type) and issubclass(type_, RapidyFieldInfo)
    except Exception:
        return False


@define(slots=True)
class HandlerRawInfo:
    return_annotation: Any
    attrs: List[Attr] = Factory(list)
    data_attrs: List[DataAttr] = Factory(list)


def get_handler_raw_info(handler: Handler) -> HandlerRawInfo:
    endpoint_signature = inspect.signature(handler)
    endpoint_signature_data = endpoint_signature.parameters
    return_annotation = endpoint_signature.return_annotation

    handler_raw_info = HandlerRawInfo(return_annotation=return_annotation)

    attribute_idx = -1
    for attribute in endpoint_signature_data.values():
        attribute_idx += 1

        if not is_empty(attribute.default):
            if isinstance(attribute.default, RapidyFieldInfo):
                data_attr = create_data_attr(
                    attribute=attribute,
                    attribute_idx=attribute_idx,
                    type_annotation=attribute.annotation,
                    raw_field_info=attribute.default,
                    annotation_def_as_annotated=False,
                    # only to create context with exception
                    handler=handler,
                )
                handler_raw_info.data_attrs.append(data_attr)
                continue

            elif is_rapidy_type(attribute.default):
                raise ParameterNotInstanceError.create(handler=handler, attr_name=attribute.name)

        if is_annotated(attribute.annotation):
            annotated_args = get_args(attribute.annotation)
            type_annotation = annotated_args[0]
            last_attr = annotated_args[-1]

            if isinstance(last_attr, RapidyFieldInfo):
                data_attr = create_data_attr(
                    attribute=attribute,
                    attribute_idx=attribute_idx,
                    type_annotation=type_annotation,
                    raw_field_info=last_attr,
                    annotation_def_as_annotated=True,
                    # only to create context with exception
                    handler=handler,
                )
                handler_raw_info.data_attrs.append(data_attr)
                continue

            elif is_rapidy_type(last_attr):
                raise ParameterNotInstanceError.create(handler=handler, attr_name=attribute.name)

        attr = Attr(
            attribute_name=attribute.name, attribute_idx=attribute_idx, attribute_annotation=attribute.annotation,
        )

        handler_raw_info.attrs.append(attr)

    return handler_raw_info
