from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError

from rapidy_core.typedefs import LocStr, ValidationErrorList

__all__ = (
    "ClientBaseError",
    "ClientError",
    "RequiredFieldIsMissingError",
    "normalize_errors",
    "regenerate_error_with_loc",
)


class ClientBaseError(ABC, ValueError):
    """Base class for validation errors produced outside a pydantic model."""

    type: str
    msg_template: str

    def __init__(self, *_: Any, **error_ctx: Any) -> None:
        self._err_msg = self.msg_template.format(**error_ctx)

    @abstractmethod
    def get_error_info(self, loc: LocStr) -> dict[str, Any]:
        """Build a pydantic-style error dictionary for ``loc``."""
        raise NotImplementedError


class ClientError(ClientBaseError, ABC):
    """Client validation error backed by pydantic-core."""

    def get_error_info(self, loc: LocStr) -> dict[str, Any]:
        err = PydanticCustomError(self.type, self._err_msg)
        loc_tuple = loc if isinstance(loc, tuple) else (loc,)
        err_details = InitErrorDetails(type=err, loc=loc_tuple, input=None)
        return dict(
            ValidationError.from_exception_data(
                title="",
                line_errors=[err_details],
                hide_input=True,
            ).errors()[0],
        )


class RequiredFieldIsMissingError(ClientError):
    """Error raised when a required field was not supplied."""

    type = "missing"
    msg_template = "Field required"


def regenerate_error_with_loc(
    *, errors: list[Any], loc: LocStr
) -> list[dict[str, Any]]:
    """Prefix every error location with ``loc``."""
    return [{**err, "loc": loc + err.get("loc", ())} for err in errors]


def error_dict_pop_useless_keys(error: dict[str, Any]) -> None:
    """Remove pydantic details omitted by the legacy rAPIdy client format."""
    error.pop("url", None)
    error.pop("input", None)


def normalize_errors(
    errors: Any | list[Any], *, pop_useless_keys: bool = True
) -> ValidationErrorList:
    """Return errors as a list, optionally removing pydantic-only detail keys."""
    if isinstance(errors, list):
        if pop_useless_keys:
            for error in errors:
                error_dict_pop_useless_keys(error)
        return errors

    if pop_useless_keys:
        error_dict_pop_useless_keys(errors)
    return [errors]
