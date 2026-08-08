from __future__ import annotations

from concurrent.futures import Executor
from http import HTTPStatus
from pprint import pformat
from typing import Any, cast, TYPE_CHECKING

from rapidy_core.client_errors import normalize_errors

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.endpoint_handlers.http.annotation_checkers import annotation_is_stream_response
from rapidy.endpoint_handlers.http.attrs_extractor import get_http_handler_info
from rapidy.endpoint_handlers.http.request.data_validators import (
    request_validator_factory,
    RequestValidator,
    result_validator_factory,
    ResultValidator,
)
from rapidy.exceptions import HTTPValidationFailure
from rapidy.request import Request
from rapidy.response import Response
from rapidy.responses.streaming import StreamResponse
from rapidy.typedefs import Handler, JSONEncoder, UnsetType, ValidationErrorList

if TYPE_CHECKING:
    from rapidy_core.encoders import CustomEncoder, Exclude, Include
    from rapidy_core.enums import ContentType

__all__ = ('HandlerController', 'ResponseValidationError', 'controller_factory')

type AttributeName = str
type AttributeValue = Any


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
        return cls.create(
            handler=handler,
            errors=pformat(normalize_errors(errors, pop_useless_keys=False)),
            **format_fields,
        )


class HandlerController:
    """Bind request validation and the temporary response contract to a handler."""

    def __init__(
        self,
        handler: Handler,
        *,
        request_validator: RequestValidator,
        result_validator: ResultValidator,
        request_attribute_name: str | None,
        response_attribute_name: str | None,
        status_code: int | HTTPStatus,
        response_validate: bool,
        response_content_type: str | ContentType | None,
        response_charset: str,
        response_zlib_executor: Executor | None,
        response_zlib_executor_size: int | None,
        response_include_fields: Include | None,
        response_exclude_fields: Exclude | None,
        response_by_alias: bool,
        response_exclude_unset: bool,
        response_exclude_defaults: bool,
        response_exclude_none: bool,
        response_custom_encoder: CustomEncoder | None,
        response_json_encoder: JSONEncoder,
    ) -> None:
        self.request_attribute_name = request_attribute_name
        self.response_attribute_name = response_attribute_name
        self._handler = handler
        self._request_validator = request_validator
        self._result_validator = result_validator
        self._status_code = status_code
        self._response_validate = response_validate
        self._response_content_type = response_content_type
        self._response_charset = response_charset
        self._response_zlib_executor = response_zlib_executor
        self._response_zlib_executor_size = response_zlib_executor_size
        self._response_include_fields = response_include_fields
        self._response_exclude_fields = response_exclude_fields
        self._response_by_alias = response_by_alias
        self._response_exclude_unset = response_exclude_unset
        self._response_exclude_defaults = response_exclude_defaults
        self._response_exclude_none = response_exclude_none
        self._response_custom_encoder = response_custom_encoder
        self._response_json_encoder = response_json_encoder

    async def validate_request(self, request: Request) -> dict[AttributeName, AttributeValue]:
        """Extract and validate all declared request-source parameters."""
        values, errors = await self._request_validator.validate(request)
        if errors:
            raise HTTPValidationFailure(errors=errors, include_pydantic_details=False)
        return cast('dict[AttributeName, AttributeValue]', values)

    async def create_response(
        self,
        handler_result: Any,
        current_response: Response | None,
    ) -> Response | StreamResponse:
        """Validate a handler result and merge it into the active response."""
        if annotation_is_stream_response(type(handler_result)):
            return cast('StreamResponse', handler_result)

        if self._response_validate:
            handler_result, validated_errors = await self._result_validator.validate(handler_result)
            if validated_errors:
                raise ResponseValidationError.create_with_handler_validation_errors(
                    handler=self._handler,
                    errors=validated_errors,
                )

        if current_response is None:
            current_response = Response(
                status=self._status_code,
                content_type=self._response_content_type,
                charset=self._response_charset,
                zlib_executor=self._response_zlib_executor,
                zlib_executor_size=self._response_zlib_executor_size,
                include=self._response_include_fields,
                exclude=self._response_exclude_fields,
                by_alias=self._response_by_alias,
                exclude_unset=self._response_exclude_unset,
                exclude_defaults=self._response_exclude_defaults,
                exclude_none=self._response_exclude_none,
                custom_encoder=self._response_custom_encoder,
                json_encoder=self._response_json_encoder,
            )
        if handler_result is None:
            return current_response

        current_response.body = handler_result
        return current_response


def controller_factory(
    endpoint_handler: Handler,
    *,
    request_attr_can_declare_fst: bool = False,
    status_code: int | HTTPStatus,
    response_validate: bool,
    response_type: type[Any] | UnsetType | None,
    response_content_type: str | ContentType | None,
    response_charset: str,
    response_zlib_executor: Executor | None,
    response_zlib_executor_size: int | None,
    response_json_encoder: JSONEncoder,
    response_include_fields: Include | None,
    response_exclude_fields: Exclude | None,
    response_by_alias: bool,
    response_exclude_unset: bool,
    response_exclude_defaults: bool,
    response_exclude_none: bool,
    response_custom_encoder: CustomEncoder | None,
) -> HandlerController:
    """Build one controller at route-registration time."""
    handler_info = get_http_handler_info(
        endpoint_handler,
        request_attr_can_declare_fst=request_attr_can_declare_fst,
    )
    request_validator = request_validator_factory(
        handler=endpoint_handler,
        request_params=handler_info.request_params,
    )
    result_validator = result_validator_factory(
        handler=endpoint_handler,
        return_annotation=handler_info.return_annotation,
        response_type=response_type,
    )
    request_attribute_name = (
        handler_info.request_attribute.attribute_name if handler_info.request_attribute is not None else None
    )
    response_attribute_name = (
        handler_info.response_attribute.attribute_name if handler_info.response_attribute is not None else None
    )
    return HandlerController(
        handler=endpoint_handler,
        request_validator=request_validator,
        result_validator=result_validator,
        request_attribute_name=request_attribute_name,
        response_attribute_name=response_attribute_name,
        status_code=status_code,
        response_validate=response_validate,
        response_content_type=response_content_type,
        response_charset=response_charset,
        response_zlib_executor=response_zlib_executor,
        response_zlib_executor_size=response_zlib_executor_size,
        response_include_fields=response_include_fields,
        response_exclude_fields=response_exclude_fields,
        response_by_alias=response_by_alias,
        response_exclude_unset=response_exclude_unset,
        response_exclude_defaults=response_exclude_defaults,
        response_exclude_none=response_exclude_none,
        response_custom_encoder=response_custom_encoder,
        response_json_encoder=response_json_encoder,
    )
