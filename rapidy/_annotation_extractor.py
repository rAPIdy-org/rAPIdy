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


class ParameterCannotBeWithDefaultError(Exception):
    pass


class IncorrectDefineDefaultValueError(Exception):
    pass


class UnsupportedSchemaDataTypeError(TypeError):
    pass


def _get_annotation_data_by_annotated_flow(
        attr_type: Any,
        param_field_info: ParamFieldInfo,
        handler: Handler,
        param: inspect.Parameter,
) -> Tuple[Any, ParamFieldInfo, Any]:
    _raise_if_annotated_def_type_cannot_default(handler=handler, field_info=param_field_info, param=param)
    _raise_if_default_value_incorrect_define(handler=handler, param=param, field_info=param_field_info)
    return attr_type, param_field_info, param.default


def _get_annotation_data_by_default_value_flow(
        handler: Handler,
        param: inspect.Parameter,
) -> Tuple[Any, ParamFieldInfo, Any]:
    field_info = _prepare_field_info(param.default)
    _raise_if_default_def_type_cannot_default(handler=handler, field_info=field_info, param=param)
    return param.annotation, field_info, param.default.default


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


def _raise_if_annotated_def_type_cannot_default(handler: Handler, param: Any, field_info: ParamFieldInfo) -> None:
    if param.default is not inspect.Signature.empty and not field_info.can_default:
        err_msg = (
            f'Handler attribute with Type `{field_info.__class__.__name__}` cannot have a default value.'
            f'{_create_handler_attr_info_msg(handler, param.name)}'
        )
        raise ParameterCannotBeWithDefaultError(err_msg)


def _raise_if_default_def_type_cannot_default(handler: Handler, param: Any, field_info: ParamFieldInfo) -> None:
    if field_info.default is not Undefined and not field_info.can_default:
        err_msg = (
            f'Handler attribute with Type `{field_info.__class__.__name__}` cannot have a default value.'
            f'{_create_handler_attr_info_msg(handler, param.name)}'
        )
        raise ParameterCannotBeWithDefaultError(err_msg)


def _raise_if_default_value_incorrect_define(handler: Handler, param: Any, field_info: ParamFieldInfo) -> None:
    if not (field_info.default is Undefined or field_info.default is Required):
        err_msg = (
            f'Default value cannot be set in `{field_info.__class__.__name__}`. '
            'Set the default value with `=` instead.'
            f'{_create_handler_attr_info_msg(handler, param.name)}'
        )
        raise IncorrectDefineDefaultValueError(err_msg)


def _raise_if_unsupported_union_schema_data_type(
        union_attributes: Sequence[Any],
        *,
        handler: Handler,
        param_name: str,
) -> None:
    if not (len(union_attributes) == 2 and type(None) in union_attributes):  # noqa: WPS516
        err_msg = f'Unsupported data type for schema. {_create_handler_attr_info_msg(handler, param_name)}'
        raise UnsupportedSchemaDataTypeError(err_msg)


def _raise_if_unsupported_attr_type(
        attr_type: Any,
        *,
        handler: Handler,
        param_name: str,
) -> None:
    try:
        is_subclass_of_base_model = issubclass(attr_type, BaseModel)
    except TypeError as type_error_exc:
        err_msg = f'Unsupported data type for schema. {_create_handler_attr_info_msg(handler, param_name)}'
        raise UnsupportedSchemaDataTypeError(err_msg) from type_error_exc

    if not (is_subclass_of_base_model or is_dataclass(attr_type)):
        err_msg = (
            'Schema annotated type must be a pydantic.BaseModel or dataclasses.dataclass.\n'
            f'{_create_handler_attr_info_msg(handler, param_name)}'
        )
        raise UnsupportedSchemaDataTypeError(err_msg)


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
