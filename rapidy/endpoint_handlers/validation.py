from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, Tuple, TypeVar

from rapidy._client_errors import regenerate_error_with_loc, RequiredFieldIsMissing
from rapidy.fields.model_fields import RapidyModelField
from rapidy.typedefs import DictStrAny, ErrorWrapper, LocStr, ValidateReturn

TData = TypeVar('TData')


class Validator(ABC, Generic[TData]):
    @abstractmethod
    async def validate(self, data: TData) -> ValidateReturn:
        raise NotImplementedError


def validate_data_by_model(  # noqa: WPS212
        model_field: RapidyModelField,
        *,
        raw_data: Any,
        loc: LocStr,
        values: DictStrAny,
) -> Tuple[Optional[Any], List[Any]]:
    if raw_data is None:
        if model_field.required:
            return values, [RequiredFieldIsMissing().get_error_info(loc=loc)]

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
