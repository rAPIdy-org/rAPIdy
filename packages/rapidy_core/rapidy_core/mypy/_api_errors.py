from __future__ import annotations

from typing import Final

from mypy.errorcodes import ErrorCode
from mypy.nodes import Context

from mypy.plugin import CheckerPluginInterface

RAPIDY_NAME: Final[str] = "rAPIdy"
"""
The name identifier for Rapidy-related error codes.
"""

ERROR_FIELD_DEFAULTS = ErrorCode("rapidy-param", "Invalid Param defaults", RAPIDY_NAME)
"""
Error code for invalid parameter defaults in Rapidy.
"""


def error_default_and_default_factory_specified(
    api: CheckerPluginInterface, context: Context
) -> None:
    """Raise a mypy error when both request parameter defaults are specified.

    This function is adapted from Pydantic's type checker implementation.

    Args:
        api (CheckerPluginInterface): The mypy plugin interface for reporting errors.
        context (Context): The context in which the error occurs.

    Returns:
        None

    """
    api.fail(
        '"default" and "default_factory" cannot be specified together for a requests parameter.',
        context,
        code=ERROR_FIELD_DEFAULTS,
    )


def error_default_or_default_factory_specified(
    api: CheckerPluginInterface, context: Context, param_name: str
) -> None:
    """Raise a mypy error when a forbidden parameter default is specified.

    Args:
        api (CheckerPluginInterface): The mypy plugin interface for reporting errors.
        context (Context): The context in which the error occurs.
        param_name (str): The name of the parameter that violates the rule.

    Returns:
        None

    """
    api.fail(
        f'"default" or "default_factory" cannot be specified for "{param_name}"',
        context,
        code=ERROR_FIELD_DEFAULTS,
    )
