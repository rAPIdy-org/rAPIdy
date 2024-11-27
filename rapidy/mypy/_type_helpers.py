from typing import Set

from mypy.types import AnyType, TypeOfAny

from rapidy.parameters import http

AnyTypeExplicit = AnyType(TypeOfAny.explicit)

RAPIDY_HTTP_PARAM_MODULE = 'rapidy.parameters.http'

ALL_RAPIDY_PARAMS: Set[str] = {f'{RAPIDY_HTTP_PARAM_MODULE}.{param}' for param in http.__all__}  # noqa: WPS407

PARAMETERS_WITHOUT_DEFAULT_VALUES: Set[str] = {  # noqa: WPS407
    # PATH
    f'{RAPIDY_HTTP_PARAM_MODULE}.PathParam',
    f'{RAPIDY_HTTP_PARAM_MODULE}.PathParams',
}


def _name_is_rapidy_param_name(name: str) -> bool:
    return name in ALL_RAPIDY_PARAMS


def _param_can_default(param_name: str) -> bool:
    return param_name not in PARAMETERS_WITHOUT_DEFAULT_VALUES
