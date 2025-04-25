from __future__ import annotations

from typing import Set

from mypy.types import AnyType, TypeOfAny

from rapidy.parameters import http

AnyTypeExplicit = AnyType(TypeOfAny.explicit)
"""
An instance of AnyType with an explicit type indicator.

Used to denote an explicitly typed Any in mypy's type system.
"""

RAPIDY_HTTP_PARAM_MODULE = 'rapidy.parameters.http'
"""
The module path for rAPIdy HTTP parameters.

Used to construct fully qualified parameter names.
"""

ALL_RAPIDY_PARAMS: Set[str] = {f'{RAPIDY_HTTP_PARAM_MODULE}.{param}' for param in http.__all__}
"""
A set of all rAPIdy HTTP parameter names.

This set is dynamically populated using the `__all__` attribute from the `rapidy.parameters.http` module.
"""

PARAMETERS_WITHOUT_DEFAULT_VALUES: Set[str] = {
    # PATH
    f'{RAPIDY_HTTP_PARAM_MODULE}.PathParam',
    f'{RAPIDY_HTTP_PARAM_MODULE}.PathParams',
}
"""
A set of rAPIdy HTTP parameter names that do not allow default values.

This includes path parameters that must always be explicitly provided.
"""


def _name_is_rapidy_param_name(name: str) -> bool:
    """
    Checks if the given name corresponds to a valid rAPIdy HTTP parameter.

    Args:
        name (str): The parameter name to check.

    Returns:
        bool: True if the name is a recognized rAPIdy HTTP parameter, False otherwise.
    """
    return name in ALL_RAPIDY_PARAMS


def _param_can_default(param_name: str) -> bool:
    """
    Determines whether the given parameter can have a default value.

    Args:
        param_name (str): The name of the parameter to check.

    Returns:
        bool: True if the parameter can have a default value, False otherwise.
    """
    return param_name not in PARAMETERS_WITHOUT_DEFAULT_VALUES
