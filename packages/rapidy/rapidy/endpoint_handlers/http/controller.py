from __future__ import annotations

from pprint import pformat
from typing import Any

from rapidy_core.client_errors import normalize_errors

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.typedefs import ValidationErrorList

__all__ = ('ResponseValidationError',)


class ResponseValidationError(RapidyHandlerException):
    """Attach response validation details to their source handler."""

    message = 'Validation errors: \n {errors}'

    @classmethod
    def create_with_handler_validation_errors(
        cls,
        handler: Any,
        *,
        errors: ValidationErrorList,
        **format_fields: str,
    ) -> RapidyHandlerException:
        """Create an error without dropping Pydantic v2 input or URL details."""
        normalized = normalize_errors(errors, pop_useless_keys=False)
        return cls.create(
            handler=handler,
            errors=pformat(normalized),
            **format_fields,
        )


# NOTE(06-extraction-pipeline): HandlerController/controller_factory join the wire pipeline there.
