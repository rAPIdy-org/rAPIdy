import inspect
from dataclasses import is_dataclass
from types import FunctionType
from typing import Any, Tuple, Union

from pydantic import BaseModel
from typing_extensions import Annotated, get_args, get_origin

from rapidy._client_errors import _create_handler_attr_info_msg
from rapidy.request_params import ParamFieldInfo
from rapidy.typedefs import Required, Undefined


class UnknownParameterError(Exception):
    pass


def extract_handler_attr_annotations(
        *,
        handler: FunctionType,
        param: inspect.Parameter,
) -> Tuple[Any, ParamFieldInfo]:
    if get_origin(param.annotation) is not Annotated:
        raise UnknownParameterError

    annotated_args = get_args(param.annotation)
    if len(annotated_args) != 2:
        raise UnknownParameterError

    attribute_type, field_info = annotated_args[0], annotated_args[1]

    if not isinstance(field_info, ParamFieldInfo):
        if isinstance(field_info, type) and issubclass(field_info, ParamFieldInfo):
            field_info = field_info()  # type: ignore[call-arg]
        else:
            raise UnknownParameterError

    if field_info.validate_type.is_schema():
        checked_attr_type = attribute_type

        if get_origin(attribute_type) is Union:
            union_attributes = get_args(attribute_type)
            assert len(union_attributes) == 2 and type(None) in union_attributes, (  # noqa: WPS516
                f'Unsupported data type for schema. {_create_handler_attr_info_msg(handler, param.name)}'
            )
            checked_attr_type = union_attributes[1] if union_attributes[0] is None else union_attributes[0]

        try:
            is_subclass_of_base_model = issubclass(checked_attr_type, BaseModel)
        except TypeError:
            err_msg = f'Unsupported data type for schema. {_create_handler_attr_info_msg(handler, param.name)}'
            raise TypeError(err_msg)

        assert is_subclass_of_base_model or is_dataclass(checked_attr_type), (
            'Schema annotated type must be a pydantic.BaseModel or dataclasses.dataclass.\n'
            f'{_create_handler_attr_info_msg(handler, param.name)}'
        )

    if param.default is not inspect.Signature.empty:
        assert field_info.can_default, (
            f'Handler attribute with Type `{field_info.__class__.__name__}` cannot have a default value.\n'
            f'{_create_handler_attr_info_msg(handler, param.name)}'
        )

    assert field_info.default is Undefined or field_info.default is Required, (
        f'Default value cannot be set in `{field_info.__class__.__name__}`. Set the default value with `=` instead.'
    )

    return attribute_type, field_info
