from typing import Any, cast, Dict, List, Optional, Tuple

from rapidy._client_errors import _regenerate_error_with_loc, RequiredFieldIsMissing
from rapidy._fields import ModelField
from rapidy.typedefs import DictStrAny, ErrorWrapper


def _validate_data_by_field(
        raw_data: Optional[Any],
        loc: Tuple[str, ...],
        model_field: ModelField,
        *,
        values: DictStrAny,
) -> Tuple[Optional[Any], List[Any]]:
    if raw_data is None:
        if model_field.required:
            return values, [RequiredFieldIsMissing().get_error_info(loc=loc)]

        return model_field.get_default(), []

    validated_data, validated_errors = model_field.validate(raw_data, values, loc=loc)
    if isinstance(validated_errors, ErrorWrapper):
        return values, [validated_errors]

    if isinstance(validated_errors, list):
        converted_errors = _regenerate_error_with_loc(errors=validated_errors, loc_prefix=())
        return values, converted_errors

    return validated_data, []


def validate_request_param_data(
        required_fields_map: Dict[str, ModelField],
        raw_data: DictStrAny,
        is_single_model: bool,
) -> Tuple[DictStrAny, List[Any]]:
    loc: Tuple[str, ...]

    if is_single_model:
        model_field = list(required_fields_map.values())[0]

        rapid_param_type = cast(str, model_field.rapid_param_type)

        loc = (rapid_param_type,)

        validated_data, validated_errors = _validate_data_by_field(
            raw_data=raw_data if raw_data else None,
            values={},
            loc=loc,
            model_field=model_field,
        )
        if validated_errors:
            return {}, validated_errors

        return {model_field.name: validated_data}, validated_errors

    all_validated_values: Dict[str, Any] = {}
    all_validated_errors: List[Dict[str, Any]] = []

    for required_field_name, model_field in required_fields_map.items():  # noqa: WPS440
        rapid_param_type = cast(str, model_field.rapid_param_type)

        loc = (rapid_param_type, model_field.alias)
        raw_param_data = raw_data.get(required_field_name)

        validated_data, validated_errors = _validate_data_by_field(
            raw_data=raw_param_data,
            values=all_validated_values,
            loc=loc,
            model_field=model_field,
        )
        if validated_errors:
            all_validated_errors.extend(validated_errors)
        else:
            all_validated_values[model_field.name] = validated_data

    return all_validated_values, all_validated_errors
