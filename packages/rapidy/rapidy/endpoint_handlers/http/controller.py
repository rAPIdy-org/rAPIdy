from __future__ import annotations

from concurrent.futures import Executor
from http import HTTPStatus
from pprint import pformat
from typing import Any, cast, Dict, Type
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
    """Exception raised when there are validation errors in the response.

    Attributes:
        message (str): Error message describing the validation failure.

    Methods:
        create_with_handler_validation_errors: Creates a new instance of `ResponseValidationError`
        with handler-specific validation errors.
    """

    message = 'Validation errors: \n {errors}'

    @classmethod
    def create_with_handler_validation_errors(
        cls,
        handler: Any,
        *,
        errors: ValidationErrorList,
        **format_fields: str,
    ) -> RapidyHandlerException:
        """Creates a `ResponseValidationError` instance with handler-specific validation errors.

        Args:
            handler (Any): The handler that caused the validation failure.
            errors (ValidationErrorList): List of validation errors.
            **format_fields (str): Additional fields for formatting the error message.

        Returns:
            RapidyHandlerException: The created `ResponseValidationError` instance.
        """
        return ResponseValidationError.create(
            handler=handler,
            errors=pformat(normalize_errors(errors)),
            **format_fields,
        )


class HandlerController:
    """Controller responsible for managing request and response validation and creation.

    Attributes:
        request_attribute_name (Optional[str]): The name of the request attribute in the handler.
        response_attribute_name (Optional[str]): The name of the response attribute in the handler.
        _handler (Handler): The handler function associated with the controller.
        _request_validator (RequestValidator): Validator for the request data.
        _result_validator (ResultValidator): Validator for the result returned by the handler.
        _status_code (int): The default status code to be used for the response.
        _response_validate (bool): Flag indicating whether to validate the response.
        _response_content_type (Union[str, ContentType, None]): The content type for the response.
        _response_charset (str): The charset for the response.
        _response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        _response_zlib_executor_size (Optional[int]): Size for the zlib compression executor.
        _response_include_fields (Optional[Include]): Fields to include in the response.
        _response_exclude_fields (Optional[Exclude]): Fields to exclude from the response.
        _response_by_alias (bool): Flag indicating whether to use field aliases in the response.
        _response_exclude_unset (bool): Flag indicating whether to exclude unset fields.
        _response_exclude_defaults (bool): Flag indicating whether to exclude default fields.
        _response_exclude_none (bool): Flag indicating whether to exclude fields with `None` values.
        _response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
        _response_json_encoder (JSONEncoder): JSON encoder for the response.

    Methods:
        validate_request: Validates the request data using the request validator.
        create_response: Creates a response based on the handler result and validates it if necessary.
    """

    def __init__(
        self,
        handler: Handler,
        *,
        request_validator: RequestValidator,
        result_validator: ResultValidator,
        # injected attr names
        request_attribute_name: str | None,
        response_attribute_name: str | None,
        # response
        status_code: int | HTTPStatus,
        response_validate: bool,
        response_content_type: str | ContentType | None,
        response_charset: str,
        response_zlib_executor: Executor | None,
        response_zlib_executor_size: int | None,
        # response json preparer
        response_include_fields: Include | None,
        response_exclude_fields: Exclude | None,
        response_by_alias: bool,
        response_exclude_unset: bool,
        response_exclude_defaults: bool,
        response_exclude_none: bool,
        response_custom_encoder: CustomEncoder | None,
        response_json_encoder: JSONEncoder,
    ) -> None:
        """Initializes the HandlerController with various parameters for request and response handling.

        Args:
            handler (Handler): The handler function for the endpoint.
            request_validator (RequestValidator): Validator for the request data.
            result_validator (ResultValidator): Validator for the result data.
            request_attribute_name (Optional[str]): The name of the request attribute.
            status_code (int): The default status code to be used for the response.
            response_attribute_name (Optional[str]): The name of the response attribute.
            response_validate (bool): Flag indicating whether the response should be validated.
            response_content_type (Union[str, ContentType, None]): The content type of the response.
            response_charset (str): The charset of the response.
            response_zlib_executor (Optional[Executor]): Executor for zlib compression.
            response_zlib_executor_size (Optional[int]): Size for the zlib compression executor.
            response_include_fields (Optional[Include]): Fields to include in the response.
            response_exclude_fields (Optional[Exclude]): Fields to exclude from the response.
            response_by_alias (bool): Flag to indicate if response should use field aliases.
            response_exclude_unset (bool): Flag to exclude unset fields from the response.
            response_exclude_defaults (bool): Flag to exclude default values from the response.
            response_exclude_none (bool): Flag to exclude `None` values from the response.
            response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.
            response_json_encoder (JSONEncoder): JSON encoder for the response.
        """
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

    async def validate_request(self, request: Request) -> Dict[AttributeName, AttributeValue]:
        """Validates the request data using the request validator.

        Args:
            request (Request): The request object containing data to validate.

        Returns:
            Dict[AttributeName, AttributeValue]: A dictionary containing the validated request data.

        Raises:
            HTTPValidationFailure: If the validation fails and errors are found in the request data.
        """
        values, errors = await self._request_validator.validate(request)
        if errors:
            raise HTTPValidationFailure(errors=errors)

        return cast(Dict[AttributeName, AttributeValue], values)

    async def create_response(self, handler_result: Any, current_response: Response | None) -> StreamResponse:
        """Creates and validates the response based on the handler result.

        Args:
            handler_result (Any): The result returned by the handler.
            current_response (Optional[Response]): The current response, if any.

        Returns:
            StreamResponse: The created or updated response.

        Raises:
            ResponseValidationError: If the response validation fails.
        """
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
    # response
    status_code: int | HTTPStatus,
    response_validate: bool,
    response_type: Type[Any] | None | UnsetType,
    response_content_type: str | ContentType | None,
    response_charset: str,
    response_zlib_executor: Executor | None,
    response_zlib_executor_size: int | None,
    response_json_encoder: JSONEncoder,
    # response json preparer
    response_include_fields: Include | None,
    response_exclude_fields: Exclude | None,
    response_by_alias: bool,
    response_exclude_unset: bool,
    response_exclude_defaults: bool,
    response_exclude_none: bool,
    response_custom_encoder: CustomEncoder | None,
) -> HandlerController:
    """Factory function for creating a HandlerController instance.

    Args:
        endpoint_handler (Handler): The endpoint handler for which to create the controller.
        request_attr_can_declare_fst (bool): Flag indicating whether request attributes can be declared fst.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Flag to indicate whether the response should be validated.
        response_type (Union[Type[Any], None, UnsetType]): The expected response type.
        response_content_type (Union[str, ContentType, None]): The content type for the response.
        response_charset (str): The charset for the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): The size for the zlib compression executor.
        response_json_encoder (JSONEncoder): JSON encoder for the response.
        response_include_fields (Optional[Include]): Fields to include in the response.
        response_exclude_fields (Optional[Exclude]): Fields to exclude from the response.
        response_by_alias (bool): Flag to use field aliases in the response.
        response_exclude_unset (bool): Flag to exclude unset fields from the response.
        response_exclude_defaults (bool): Flag to exclude default fields from the response.
        response_exclude_none (bool): Flag to exclude `None` fields from the response.
        response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.

    Returns:
        HandlerController: The created HandlerController instance.
    """
    http_handler_info = get_http_handler_info(
        endpoint_handler,
        request_attr_can_declare_fst=request_attr_can_declare_fst,
    )

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
