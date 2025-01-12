from concurrent.futures import Executor
from pprint import pformat
from typing import Any, cast, Dict, Optional, Type, Union
from typing_extensions import TypeAlias

from rapidy._base_exceptions import RapidyHandlerException
from rapidy._client_errors import normalize_errors
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.endpoint_handlers.http.annotation_checkers import annotation_is_stream_response
from rapidy.endpoint_handlers.http.attrs_extractor import get_http_handler_info
from rapidy.endpoint_handlers.http.request.data_validators import (
    request_validator_factory,
    RequestValidator,
    result_validator_factory,
    ResultValidator,
)
from rapidy.enums import ContentType
from rapidy.typedefs import Handler, JSONEncoder, UnsetType, ValidationErrorList
from rapidy.web_exceptions import HTTPValidationFailure
from rapidy.web_request import Request
from rapidy.web_response import Response, StreamResponse

AttributeName: TypeAlias = str
AttributeValue: TypeAlias = Any


class ResponseValidationError(RapidyHandlerException):
    message = 'Validation errors: \n {errors}'

    @classmethod
    def create_with_handler_validation_errors(
        cls,
        handler: Any,
        *,
        errors: ValidationErrorList,
        **format_fields: str,
    ) -> 'RapidyHandlerException':
        return ResponseValidationError.create(
            handler=handler,
            errors=pformat(normalize_errors(errors)),
            **format_fields,
        )


class HandlerController:
    def __init__(
        self,
        handler: Handler,
        *,
        request_validator: RequestValidator,
        result_validator: ResultValidator,
        # injected attr names
        request_attribute_name: Optional[str],
        response_attribute_name: Optional[str],
        # response
        response_validate: bool,
        response_content_type: Union[str, ContentType, None],
        response_charset: str,
        response_zlib_executor: Optional[Executor],
        response_zlib_executor_size: Optional[int],
        # response json preparer
        response_include_fields: Optional[Include],
        response_exclude_fields: Optional[Exclude],
        response_by_alias: bool,
        response_exclude_unset: bool,
        response_exclude_defaults: bool,
        response_exclude_none: bool,
        response_custom_encoder: Optional[CustomEncoder],
        response_json_encoder: JSONEncoder,
    ) -> None:
        self._handler = handler

        self._request_validator = request_validator
        self._result_validator = result_validator

        self.request_attribute_name = request_attribute_name
        self.response_attribute_name = response_attribute_name

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

    async def validate_request(self, request: Request) -> Dict[AttributeName, AttributeValue]:
        values, errors = await self._request_validator.validate(request)
        if errors:
            raise HTTPValidationFailure(errors=errors)

        return cast(Dict[AttributeName, AttributeValue], values)

    async def create_response(self, handler_result: Any, current_response: Optional[Response]) -> StreamResponse:
        if annotation_is_stream_response(type(handler_result)):
            return handler_result

        if self._response_validate:
            handler_result, validated_errors = await self._result_validator.validate(handler_result)
            if validated_errors:
                raise ResponseValidationError.create_with_handler_validation_errors(
                    handler=self._handler,
                    errors=validated_errors,
                )

        if current_response is None:
            current_response = Response(
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
    request_attr_can_declare: bool = False,
    # response
    response_validate: bool,
    response_type: Union[Type[Any], None, UnsetType],
    response_content_type: Union[str, ContentType, None],
    response_charset: str,
    response_zlib_executor: Optional[Executor],
    response_zlib_executor_size: Optional[int],
    response_json_encoder: JSONEncoder,
    # response json preparer
    response_include_fields: Optional[Include],
    response_exclude_fields: Optional[Exclude],
    response_by_alias: bool,
    response_exclude_unset: bool,
    response_exclude_defaults: bool,
    response_exclude_none: bool,
    response_custom_encoder: Optional[CustomEncoder],
) -> HandlerController:
    http_handler_info = get_http_handler_info(endpoint_handler, request_attr_can_declare=request_attr_can_declare)

    # validators
    request_validator = request_validator_factory(
        handler=endpoint_handler,
        request_params=http_handler_info.request_params,
    )
    result_validator = result_validator_factory(
        handler=endpoint_handler,
        return_annotation=http_handler_info.return_annotation,
        response_type=response_type,
    )

    # injected attr names
    request_attribute_name = (
        http_handler_info.request_attribute.attribute_name if http_handler_info.request_attribute else None
    )
    response_attribute_name = (
        http_handler_info.response_attribute.attribute_name if http_handler_info.response_attribute else None
    )

    return HandlerController(
        handler=endpoint_handler,
        # validators
        request_validator=request_validator,
        result_validator=result_validator,
        # injected attr names
        request_attribute_name=request_attribute_name,
        response_attribute_name=response_attribute_name,
        # response attrs
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
