import inspect
from dataclasses import is_dataclass
from typing import Any, cast, Sequence, Tuple, Type, Union

from pydantic import BaseModel
from typing_extensions import Annotated, get_args, get_origin

from rapidy._client_errors import _create_handler_attr_info_msg
from rapidy.request_params import ParamFieldInfo
from rapidy.typedefs import Handler, Required, Undefined


class NotParameterError(Exception):
    pass


class ParameterCannotHaveDefaultError(Exception):
    _base_err_msg = 'Handler attribute with Type `{class_name}` cannot have a default value.'

    def __init__(self, *args: Any, class_name: str, handler: Any, param_name: str) -> None:
        super().__init__(
            f'{self._base_err_msg.format(class_name=class_name)}\n{_create_handler_attr_info_msg(handler, param_name)}',
            *args,
        )


class ParameterCannotHaveDefaultFactoryError(Exception):
    _base_err_msg = 'Handler attribute with Type `{class_name}` cannot have a default_factory.'

    def __init__(self, *args: Any, class_name: str, handler: Any, param_name: str) -> None:
        super().__init__(
            f'{self._base_err_msg.format(class_name=class_name)}\n{_create_handler_attr_info_msg(handler, param_name)}',
            *args,
        )


class SpecifyBothDefaultAndDefaultFactoryError(TypeError):
    _base_err_msg = 'Cannot specify both default and default_factory in `{class_name}`.'

    def __init__(self, *args: Any, class_name: str, handler: Any, param_name: str) -> None:
        super().__init__(
            f'{self._base_err_msg.format(class_name=class_name)}\n{_create_handler_attr_info_msg(handler, param_name)}',
            *args,
        )


class IncorrectDefineDefaultValueError(Exception):
    _base_err_msg = (
        'Default value cannot be set in `{class_name}`. '
        'You cannot specify a default value using Param(<default_value>, ...) and `=` at the same time.'
    )

    def __init__(self, *args: Any, class_name: str, handler: Any, param_name: str) -> None:
        super().__init__(
            f'{self._base_err_msg.format(class_name=class_name)}\n{_create_handler_attr_info_msg(handler, param_name)}',
            *args,
        )


class UnsupportedSchemaDataTypeError(TypeError):
    def __init__(self, *args: Any, err_msg: str, handler: Any, param_name: str) -> None:
        super().__init__(
            f'{err_msg}\n{_create_handler_attr_info_msg(handler, param_name)}',
            *args,
        )


def _get_annotation_data_by_annotated_flow(
        attr_type: Any,
        param_field_info: ParamFieldInfo,
        handler: Handler,
        param: inspect.Parameter,
) -> Tuple[Any, ParamFieldInfo, Any]:
    default = _get_annotated_definition_attr_default(handler=handler, field_info=param_field_info, param=param)
    return attr_type, param_field_info, default


def _get_annotation_data_by_default_value_flow(
        handler: Handler,
        param: inspect.Parameter,
) -> Tuple[Any, ParamFieldInfo, Any]:
    field_info = _prepare_field_info(param.default)
    default = _get_default_definition_attr_default(handler=handler, field_info=field_info, param_name=param.name)
    return param.annotation, field_info, default


def _get_annotation_data(
        handler: Handler,
        param: Any,
) -> Tuple[Any, ParamFieldInfo, Any]:
    annotation_origin = get_origin(param.annotation)

    if annotation_origin is Annotated:
        annotated_args = get_args(param.annotation)
        if len(annotated_args) != 2:
            raise NotParameterError

        return _get_annotation_data_by_annotated_flow(
            attr_type=annotated_args[0],
            param_field_info=_prepare_field_info(annotated_args[1]),
            handler=handler,
            param=param,
        )

    if param.default is inspect.Signature.empty:
        raise NotParameterError

    return _get_annotation_data_by_default_value_flow(
        handler=handler,
        param=param,
    )


def _prepare_field_info(raw_field_info: Union[ParamFieldInfo, Type[ParamFieldInfo]]) -> ParamFieldInfo:
    if not isinstance(raw_field_info, ParamFieldInfo):
        if isinstance(raw_field_info, type) and issubclass(raw_field_info, ParamFieldInfo):
            raw_field_info = raw_field_info()
        else:
            raise NotParameterError

    return cast(ParamFieldInfo, raw_field_info)


def _get_annotated_definition_attr_default(
        handler: Handler,
        param: Any,
        field_info: ParamFieldInfo,
) -> Any:
    param_default_exist = param.default is not inspect.Signature.empty
    field_default_exist = not (field_info.default is Undefined or field_info.default is Required)
    field_default_factory_exist = field_info.default_factory is not None

    default_exist = param_default_exist or field_default_exist
    can_default = field_info.can_default and not field_info.validate_type.is_no_validate()

    if default_exist and not can_default:
        raise ParameterCannotHaveDefaultError(
            class_name=field_info.__class__.__name__,
            handler=handler,
            param_name=param.name,
        )

    if field_default_factory_exist and not can_default:
        raise ParameterCannotHaveDefaultFactoryError(
            class_name=field_info.__class__.__name__,
            handler=handler,
            param_name=param.name,
        )

    if default_exist and field_default_factory_exist:
        if field_info.default_factory is not None:
            raise SpecifyBothDefaultAndDefaultFactoryError(
                class_name=field_info.__class__.__name__,
                handler=handler,
                param_name=param.name,
            )

    if param_default_exist and field_default_exist:
        raise IncorrectDefineDefaultValueError(
            class_name=field_info.__class__.__name__,
            handler=handler,
            param_name=param.name,
        )

    default = inspect.Signature.empty

    if param_default_exist:
        default = param.default

    elif field_default_exist:
        default = field_info.default

    return default


def _get_default_definition_attr_default(
        handler: Handler,
        param_name: str,
        field_info: ParamFieldInfo,
) -> Any:
    can_default = field_info.can_default and not field_info.validate_type.is_no_validate()

    if field_info.default is not Undefined and not can_default:
        raise ParameterCannotHaveDefaultError(
            class_name=field_info.__class__.__name__,
            handler=handler,
            param_name=param_name,
        )

    if field_info.default_factory is not None and not can_default:
        raise ParameterCannotHaveDefaultFactoryError(
            class_name=field_info.__class__.__name__,
            handler=handler,
            param_name=param_name,
        )

    return field_info.default


def _raise_if_unsupported_union_schema_data_type(
        union_attributes: Sequence[Any],
        *,
        handler: Handler,
        param_name: str,
) -> None:
    if not (len(union_attributes) == 2 and type(None) in union_attributes):  # noqa: WPS516
        raise UnsupportedSchemaDataTypeError(
            err_msg='Schema annotated type must be a pydantic.BaseModel or dataclasses.dataclass.',
            handler=handler,
            param_name=param_name,
        )


def _raise_if_unsupported_attr_type(
        attr_type: Any,
        *,
        handler: Handler,
        param_name: str,
) -> None:
    try:
        is_subclass_of_base_model = issubclass(attr_type, BaseModel)
    except TypeError as type_error_exc:
        raise UnsupportedSchemaDataTypeError(
            err_msg='Unsupported data type for schema.',
            handler=handler,
            param_name=param_name,
        ) from type_error_exc

    if not (is_subclass_of_base_model or is_dataclass(attr_type)):
        raise UnsupportedSchemaDataTypeError(
            err_msg='Schema annotated type must be a pydantic.BaseModel or dataclasses.dataclass.',
            handler=handler,
            param_name=param_name,
        )


def extract_handler_attr_annotations(
        *,
        handler: Handler,
        param: inspect.Parameter,
) -> Tuple[Any, ParamFieldInfo, Any]:
    attribute_type, field_info, default = _get_annotation_data(handler, param)

    if field_info.validate_type.is_schema():
        checked_attr_type = attribute_type

        if get_origin(attribute_type) is Union:
            union_attributes = get_args(attribute_type)

            _raise_if_unsupported_union_schema_data_type(union_attributes, handler=handler, param_name=param.name)

            checked_attr_type = union_attributes[1] if union_attributes[0] is None else union_attributes[0]

        _raise_if_unsupported_attr_type(checked_attr_type, handler=handler, param_name=param.name)

    return attribute_type, field_info, default
