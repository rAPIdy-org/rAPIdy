from functools import cache
from typing import Callable, Dict, List, Set

from mypy.checker import TypeChecker
from mypy.plugin import CheckerPluginInterface
from mypy.types import AnyType, Instance, Type, TypeOfAny
from typing_extensions import TypeAlias

from rapidy.mypy._version import MYPY_VERSION_TUPLE

DefaultAnyType: Type = AnyType(TypeOfAny.explicit)

RAPIDY_PARAM_BASE = 'rapidy.request_params.'
BUILTINS_NAME = 'builtins' if MYPY_VERSION_TUPLE >= (0, 930) else '__builtins__'
DICT_NAME = f'{BUILTINS_NAME}.dict'
STR_NAME = f'{BUILTINS_NAME}.str'
BYTES_NAME = f'{BUILTINS_NAME}.bytes'
LIST_NAME = f'{BUILTINS_NAME}.list'

PARAMETERS_WITHOUT_DEFAULT_VALUES: Set[str] = {  # noqa: WPS407
    # PATH
    f'{RAPIDY_PARAM_BASE}Path',
    f'{RAPIDY_PARAM_BASE}PathSchema',
    f'{RAPIDY_PARAM_BASE}PathRaw',
    # HEADER
    f'{RAPIDY_PARAM_BASE}HeaderRaw',
    # COOKIE
    f'{RAPIDY_PARAM_BASE}CookieRaw',
    # QUERY
    f'{RAPIDY_PARAM_BASE}QueryRaw',
    # BODY
    f'{RAPIDY_PARAM_BASE}StreamBody',
    f'{RAPIDY_PARAM_BASE}BytesBody',
    f'{RAPIDY_PARAM_BASE}TextBody',
    f'{RAPIDY_PARAM_BASE}JsonBodyRaw',
    f'{RAPIDY_PARAM_BASE}FormDataBodyRaw',
    f'{RAPIDY_PARAM_BASE}MultipartBodyRaw',
}


@cache
def create_str_mypy_type(api: TypeChecker) -> Type:
    return api.named_type(STR_NAME)


@cache
def create_bytes_mypy_type(api: TypeChecker) -> Type:
    return api.named_type(BYTES_NAME)


def create_list_mypy_type(api: TypeChecker, generic_types: List[Type]) -> Type:
    return api.named_generic_type(LIST_NAME, generic_types)


def create_dict_mypy_type(api: TypeChecker, generic_types: List[Type]) -> Type:
    return api.named_generic_type(DICT_NAME, generic_types)


@cache
def create_list_any_mypy_type(api: TypeChecker) -> Type:
    return create_list_mypy_type(api, [DefaultAnyType])


@cache
def create_list_str_mypy_type(api: TypeChecker) -> Type:
    str_type = create_str_mypy_type(api)
    return create_list_mypy_type(api, [str_type])


@cache
def create_dict_str_str_mypy_type(api: TypeChecker) -> Type:
    str_type = create_str_mypy_type(api)
    return create_dict_mypy_type(api, [str_type, str_type])


@cache
def create_dict_str_any_mypy_type(api: TypeChecker) -> Type:
    str_type = create_str_mypy_type(api)
    return create_dict_mypy_type(api, [str_type, DefaultAnyType])


@cache
def create_dict_str_list_any_mypy_type(api: TypeChecker) -> Type:
    str_type = create_str_mypy_type(api)
    list_any = create_list_any_mypy_type(api)
    return create_dict_mypy_type(api, [str_type, list_any])


@cache
def create_dict_str_list_str_mypy_type(api: TypeChecker) -> Type:
    str_type = create_str_mypy_type(api)
    list_str = create_list_str_mypy_type(api)
    return create_dict_mypy_type(api, [str_type, list_str])


@cache
def create_stream_reader_mypy_type(api: TypeChecker) -> Type:
    stream_reader_symbol_table_node = api.modules['rapidy.streams'].names['StreamReader']
    type_info = stream_reader_symbol_table_node.node
    return Instance(type_info, [])  # type: ignore[arg-type]


def create_form_data_raw_type(
        api: CheckerPluginInterface,
        duplicated_attrs_parse_as_array: bool,
) -> Type:
    if duplicated_attrs_parse_as_array:
        return create_dict_str_list_str_mypy_type(api)

    return create_dict_str_str_mypy_type(api)


def create_multipart_raw_type(
        api: CheckerPluginInterface,
        duplicated_attrs_parse_as_array: bool,
) -> Type:
    if duplicated_attrs_parse_as_array:
        return create_dict_str_list_any_mypy_type(api)

    return create_dict_str_any_mypy_type(api)


CreatedTypeFunc: TypeAlias = Callable[[CheckerPluginInterface], Type]
# only for form-data and multipart raw
CreatedDynamicTypeFunc: TypeAlias = Callable[[CheckerPluginInterface, bool], Type]

return_static_type_map: Dict[str, CreatedTypeFunc] = {
    'PathRaw': create_dict_str_str_mypy_type,
    'HeaderRaw': create_dict_str_str_mypy_type,
    'CookieRaw': create_dict_str_str_mypy_type,
    'QueryRaw': create_dict_str_str_mypy_type,
    'TextBody': create_str_mypy_type,
    'BytesBody': create_bytes_mypy_type,
    'StreamBody': create_stream_reader_mypy_type,
    'JsonBodyRaw': create_dict_str_any_mypy_type,
}
return_dynamic_type_map: Dict[str, CreatedDynamicTypeFunc] = {
    'FormDataBodyRaw': create_form_data_raw_type,
    'MultipartBodyRaw': create_multipart_raw_type,
}


def _name_is_rapidy_param_name(name: str) -> bool:
    return name.startswith(RAPIDY_PARAM_BASE)


def _param_can_default(param_name: str) -> bool:
    return param_name not in PARAMETERS_WITHOUT_DEFAULT_VALUES
