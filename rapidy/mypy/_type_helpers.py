from functools import cache
from typing import Callable, Dict, List, Set

from mypy.checker import TypeChecker
from mypy.plugin import CheckerPluginInterface
from mypy.types import AnyType, Instance, Type, TypeOfAny, UnionType
from typing_extensions import TypeAlias

from rapidy.mypy._version import MYPY_VERSION_TUPLE

RAPIDY_PARAM_BASE = 'rapidy.request_params.'
BUILTINS_NAME = 'builtins' if MYPY_VERSION_TUPLE >= (0, 930) else '__builtins__'


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


class TypeCreator:

    @staticmethod
    @cache
    def string(api: TypeChecker) -> Type:
        return api.str_type()

    @staticmethod
    @cache
    def bytes(api: TypeChecker) -> Type:
        return api.named_type(f'{BUILTINS_NAME}.bytes')

    @staticmethod
    def list(api: TypeChecker, generic_types: List[Type]) -> Type:
        return api.named_generic_type(f'{BUILTINS_NAME}.list', generic_types)

    @staticmethod
    @cache
    def list_str(api: TypeChecker) -> Type:
        return TypeCreator.list(api, [TypeCreator.string(api)])

    @staticmethod
    @cache
    def list_any(api: TypeChecker) -> Type:
        return TypeCreator.list(api, [TypeCreator.any_explicit()])

    @staticmethod
    def dict(api: TypeChecker, generic_types: List[Type]) -> Type:
        return api.named_generic_type(f'{BUILTINS_NAME}.dict', generic_types)

    @staticmethod
    @cache
    def dict_str_str(api: TypeChecker) -> Type:
        return TypeCreator.dict(api, [TypeCreator.string(api), TypeCreator.string(api)])

    @staticmethod
    @cache
    def dict_str_union_str_list_str(api: TypeChecker) -> Type:
        return TypeCreator.dict(
            api, [TypeCreator.string(api), UnionType([TypeCreator.string(api), TypeCreator.list_str(api)])],
        )

    @staticmethod
    @cache
    def dict_str_any(api: TypeChecker) -> Type:
        return TypeCreator.dict(api, [TypeCreator.string(api), AnyType(TypeOfAny.explicit)])

    @staticmethod
    @cache
    def dict_str_union_any_list_any(api: TypeChecker) -> Type:
        return TypeCreator.dict(
            api, [TypeCreator.string(api), UnionType([TypeCreator.any_explicit(), TypeCreator.list_any(api)])],
        )

    @staticmethod
    @cache
    def any_explicit() -> Type:  # noqa: WPS605
        return AnyType(TypeOfAny.explicit)

    @staticmethod
    @cache
    def stream_reader(api: TypeChecker) -> Type:
        stream_reader_symbol_table_node = api.modules['rapidy.streams'].names['StreamReader']
        type_info = stream_reader_symbol_table_node.node
        return Instance(type_info, [])  # type: ignore[arg-type]


def create_form_data_raw_type(
        api: CheckerPluginInterface,
        duplicated_attrs_parse_as_array: bool,
) -> Type:
    if duplicated_attrs_parse_as_array:
        return TypeCreator.dict_str_union_str_list_str(api)

    return TypeCreator.dict_str_str(api)


def create_multipart_raw_type(
        api: CheckerPluginInterface,
        duplicated_attrs_parse_as_array: bool,
) -> Type:
    if duplicated_attrs_parse_as_array:
        return TypeCreator.dict_str_union_any_list_any(api)

    return TypeCreator.dict_str_any(api)


CreatedTypeFunc: TypeAlias = Callable[[CheckerPluginInterface], Type]
# only for form-data and multipart raw
CreatedDynamicTypeFunc: TypeAlias = Callable[[CheckerPluginInterface, bool], Type]

return_static_type_map: Dict[str, CreatedTypeFunc] = {
    'PathRaw': TypeCreator.dict_str_str,
    'HeaderRaw': TypeCreator.dict_str_str,
    'CookieRaw': TypeCreator.dict_str_str,
    'QueryRaw': TypeCreator.dict_str_str,
    'TextBody': TypeCreator.string,
    'BytesBody': TypeCreator.bytes,
    'StreamBody': TypeCreator.stream_reader,
    'JsonBodyRaw': TypeCreator.dict_str_any,
}
return_dynamic_type_map: Dict[str, CreatedDynamicTypeFunc] = {
    'FormDataBodyRaw': create_form_data_raw_type,
    'MultipartBodyRaw': create_multipart_raw_type,
}


def _name_is_rapidy_param_name(name: str) -> bool:
    return name.startswith(RAPIDY_PARAM_BASE)


def _param_can_default(param_name: str) -> bool:
    return param_name not in PARAMETERS_WITHOUT_DEFAULT_VALUES
