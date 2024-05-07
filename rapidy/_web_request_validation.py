from typing import Any, cast, Dict, List, TYPE_CHECKING

from rapidy._annotation_container import AnnotationContainer

if TYPE_CHECKING:
    from rapidy.web_request import Request

from rapidy._client_errors import _normalize_errors
from rapidy.web_exceptions import HTTPValidationFailure


async def _validate_request(
        request: 'Request',
        *,
        annotation_container: AnnotationContainer,
        errors_response_field_name: str,
) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []

    for param_container in annotation_container:
        param_values, param_errors = await param_container.get_request_data(request)
        if param_errors:
            errors += param_errors
        else:
            values.update(cast(Dict[str, Any], param_values))

    if errors:
        raise HTTPValidationFailure(
            validation_failure_field_name=errors_response_field_name,
            errors=_normalize_errors(errors),
        )

    return values
