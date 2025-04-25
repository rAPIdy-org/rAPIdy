from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Tuple, TypeVar

from rapidy._client_errors import regenerate_error_with_loc, RequiredFieldIsMissingError
from rapidy.fields.model_fields import RapidyModelField
from rapidy.typedefs import DictStrAny, ErrorWrapper, LocStr, ValidateReturn

TData = TypeVar('TData')


class Validator(ABC, Generic[TData]):
    """Abstract base class for validating data.

    This class should be inherited and the `validate` method implemented to define custom validation logic.

    Attributes:
        TData (TypeVar): Type variable for the data to be validated.
    """

    @abstractmethod
    async def validate(self, data: TData) -> ValidateReturn:
        """Validates the provided data.

        Args:
            data (TData): The data to validate.

        Returns:
            ValidateReturn: The result of the validation, which could either be valid data or errors.
        """
        raise NotImplementedError


def validate_data_by_model(
    model_field: RapidyModelField,
    *,
    raw_data: Any,
    loc: LocStr,
    values: DictStrAny,
) -> Tuple[Any | None, List[Any]]:
    """Validates data according to a model field's rules and returns any validation errors.

    This function handles different cases based on the presence of raw data, model field settings,
    and whether the field requires validation or not.

    Args:
        model_field (RapidyModelField): The model field containing validation rules.
        raw_data (Any): The raw data to validate.
        loc (LocStr): The location where the error occurred (used for error reporting).
        values (DictStrAny): The existing values to validate against.

    Returns:
        Tuple[Optional[Any], List[Any]]: A tuple containing the validated data (or default if no data),
            and a list of errors encountered during validation (if any). If no errors, the list is empty.
    """
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
    if isinstance(validated_errors, ErrorWrapper):
        return values, [validated_errors]

    if isinstance(validated_errors, list):
        converted_errors = regenerate_error_with_loc(errors=validated_errors, loc=())
        return values, converted_errors

    return validated_data, []
