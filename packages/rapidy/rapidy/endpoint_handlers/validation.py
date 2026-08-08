from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from rapidy_core.client_errors import RequiredFieldIsMissingError

if TYPE_CHECKING:
    from rapidy_core.fields import RapidyModelField
    from rapidy_core.typedefs import DictStrAny, LocStr, ValidateReturn

__all__ = ('Validator', 'validate_data_by_model')

class Validator[TData](ABC):
    """Base interface for async request and result validators."""

    @abstractmethod
    async def validate(self, data: TData) -> ValidateReturn:
        """Validate data and return a value/error pair."""
        raise NotImplementedError


def validate_data_by_model(
    model_field: RapidyModelField,
    *,
    raw_data: Any,
    loc: LocStr,
    values: DictStrAny,
) -> tuple[Any | None, list[dict[str, Any]]]:
    """Validate one raw value with a shared core model field."""
    if raw_data is None:
        if model_field.required:
            return values, [RequiredFieldIsMissingError().get_error_info(loc=loc)]
        return model_field.get_default(), []

    if model_field.default_exists and not raw_data:
        if model_field.field_info.default is None:
            return None, []
        return model_field.get_default(), []

    if not model_field.need_validate:
        return raw_data, []

    validated_data, validated_errors = model_field.validate(raw_data, values, loc=loc)
    if validated_errors:
        return values, validated_errors
    return validated_data, []
