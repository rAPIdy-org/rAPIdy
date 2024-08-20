from typing import Set

from rapidy import request_parameters

RAPIDY_PARAM_BASE = 'rapidy.request_parameters.'

ALL_RAPIDY_PARAMS: Set[str] = {f'{RAPIDY_PARAM_BASE}{param}' for param in request_parameters.__all__}  # noqa: WPS407

PARAMETERS_WITHOUT_DEFAULT_VALUES: Set[str] = {  # noqa: WPS407
    # PATH
    f'{RAPIDY_PARAM_BASE}PathParam',
    f'{RAPIDY_PARAM_BASE}PathParams',
}


def _name_is_rapidy_param_name(name: str) -> bool:
    return name in ALL_RAPIDY_PARAMS


def _param_can_default(param_name: str) -> bool:
    return param_name not in PARAMETERS_WITHOUT_DEFAULT_VALUES
