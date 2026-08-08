from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import is_dataclass
from typing import Any, cast, Dict, get_args, Iterable, List, Mapping, Type, Union

from multidict import MultiDict, MultiDictProxy

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.annotation_checkers import is_empty, is_union
from rapidy.endpoint_handlers.http.annotation_checkers import annotation_is_stream_response
from rapidy.endpoint_handlers.http.attrs_extractor import HTTPRequestAttr
from rapidy.endpoint_handlers.http.fields import create_request_model_field, RequestModelField
from rapidy.endpoint_handlers.http.request.data_extractors import ExtractError, get_extractor
from rapidy.endpoint_handlers.validation import validate_data_by_model, Validator
from rapidy.enums import HTTPRequestParamType
from rapidy.fields.model_fields import create_model_field_by_annotation, RapidyModelField
from rapidy.parameters.http import RequestParamFieldInfo
from rapidy.typedefs import Handler, ResultValidate, Unset, UnsetType, ValidateReturn
from rapidy.web_request import Request


class AnotherDataExtractionTypeAlreadyExistsError(RapidyHandlerException):
    """Raised when another data extraction type is already in use in the handler.

    Attributes:
        message (str): Error message describing the conflict.
    """

    message = (
        'Attribute with this data extraction type cannot be added to the handler - '
        'another data extraction type is already use in handler.'
    )


class AttributeAlreadyExistsError(RapidyHandlerException):
    """Raised when an attribute with the same name or alias already exists.

    Attributes:
        message (str): Error message describing the conflict.
    """

    message = 'Attribute with this name or alias already exists.'


class BaseRequestValidator(Validator[Request], ABC):
    """Base class for request validators.

    Inherits from `Validator` and serves as a base for specific request validation logic.
    """


class BaseRequestParameterValidator(BaseRequestValidator, ABC):
    """Base class for validating request parameters.

    Attributes:
        _extractor (Any): Function for extracting raw data from the request.
        _http_request_param_type (HTTPRequestParamType): Type of the HTTP request parameter.
        _map_model_fields_by_alias (Dict[str, RequestModelField]): Mapping of model fields by alias.

    Args:
        extractor (Any): Function for extracting raw data from the request.
        http_request_param_type (HTTPRequestParamType): Type of the HTTP request parameter.
    """

    def __init__(self, extractor: Any, http_request_param_type: HTTPRequestParamType) -> None:
        self._extractor = extractor
        self._http_request_param_type = http_request_param_type
        self._map_model_fields_by_alias: Dict[str, RequestModelField] = {}

    async def validate(self, request: Request) -> ValidateReturn:
        """Validates the request by extracting and validating data.

        Args:
            request (Request): The incoming HTTP request.

        Returns:
            ValidateReturn: A tuple containing validated values and any validation errors.
        """
        try:
            raw_data = await self._extract_raw_data(request)
        except ExtractError as exc:
            return {}, [exc.get_error_info(loc=(self._http_request_param_type,))]

        return await self._get_validated_data(raw_data=raw_data, required_fields_map=self._map_model_fields_by_alias)

    def add_field(self, field_info: RequestParamFieldInfo, handler: Handler) -> None:
        """Adds a field to the validator.

        Args:
            field_info (RequestParamFieldInfo): Information about the request parameter field.
            handler (Handler): The handler for this request.

        Raises:
            AttributeAlreadyExistsError: If an attribute with the same name or alias already exists.
        """
        model_field = create_request_model_field(field_info=field_info)
        extraction_name = model_field.alias or model_field.name

        if self._map_model_fields_by_alias.get(extraction_name):
            raise AttributeAlreadyExistsError.create(handler=handler, attr_name=field_info.name)

        self._map_model_fields_by_alias[extraction_name] = model_field

    async def _extract_raw_data(self, request: Request) -> Any:
        """Extracts raw data from the request.

        Args:
            request (Request): The incoming HTTP request.

        Returns:
            Any: The extracted raw data from the request.
        """
        raw_data = request._cache.get(self._http_request_param_type)  # noqa: SLF001

        if not raw_data:
            raw_data = await self._extractor(request)
            request._cache[self._http_request_param_type] = raw_data  # noqa: SLF001

        return raw_data

    @abstractmethod
    async def _get_validated_data(
        self,
        raw_data: Any,
        required_fields_map: Dict[str, RequestModelField],
    ) -> ValidateReturn:
        """Validates the extracted raw data.

        Args:
            raw_data (Any): The raw data extracted from the request.
            required_fields_map (Dict[str, RequestModelField]): Mapping of required model fields.

        Returns:
            ValidateReturn: A tuple containing validated data and validation errors.
        """
        raise NotImplementedError


class RequestSingleParameterValidator(BaseRequestParameterValidator):
    """Validator for single request parameters.

    Inherits from `BaseRequestParameterValidator` and handles validation of individual parameters.

    Args:
        raw_data (Any): The raw data extracted from the request.
        required_fields_map (Dict[str, RequestModelField]): Mapping of required model fields.
    """

    async def _get_validated_data(
        self,
        raw_data: Any,
        required_fields_map: Dict[str, RequestModelField],
    ) -> ValidateReturn:
        all_validated_values: Dict[str, Any] = {}
        all_validated_errors: List[Dict[str, Any]] = []

        for required_field_name, model_field in required_fields_map.items():
            loc = (model_field.http_param_type, model_field.alias)
            raw_param_data = raw_data.get(required_field_name) if raw_data is not None else None

            validated_data, validated_errors = validate_data_by_model(
                model_field,
                raw_data=raw_param_data,
                values=all_validated_values,
                loc=loc,
            )
            if validated_errors:
                all_validated_errors.extend(validated_errors)
            else:
                all_validated_values[model_field.name] = validated_data

        return all_validated_values, all_validated_errors


class RequestAllDataParameterValidator(BaseRequestParameterValidator):
    """Validator for all data parameters in the request.

    Handles validation when multiple parameters are extracted together, typically for complex data structures.

    Args:
        raw_data (Any): The raw data extracted from the request.
        required_fields_map (Dict[str, RequestModelField]): Mapping of required model fields.
    """

    async def _get_validated_data(
        self,
        raw_data: Any,
        required_fields_map: Dict[str, RequestModelField],
    ) -> ValidateReturn:
        model_field = list(required_fields_map.values())[0]  # noqa: RUF015

        if is_dataclass(model_field.type_) and isinstance(raw_data, MultiDict | MultiDictProxy | Mapping):
            raw_data = self._create_dataclass_raw_data_by_multidict(raw_data, model_field_type=model_field.type_)

        validated_data, validated_errors = validate_data_by_model(
            model_field,
            raw_data=raw_data,
            values={},
            loc=(model_field.field_info.param_type,),
        )
        if validated_errors:
            return {}, validated_errors

        return {model_field.name: validated_data}, validated_errors

    def _create_dataclass_raw_data_by_multidict(
        self,
        current_raw: Any,
        *,
        model_field_type: Any,
    ) -> Dict[str, Any]:
        """Creates raw data for a dataclass from a MultiDict.

        Args:
            current_raw (Any): The raw data to convert.
            model_field_type (Any): The type of the dataclass.

        Returns:
            Dict[str, Any]: The raw data as a dictionary with dataclass attribute names as keys.
        """
        dataclass_attrs = inspect.signature(model_field_type).parameters.keys()
        return {attr_name: current_raw.get(attr_name) for attr_name in dataclass_attrs if attr_name in current_raw}


class RequestValidator(BaseRequestValidator):
    """Validator for the entire request.

    Validates request parameters using a list of parameter validators.

    Args:
        request_parameter_handlers (Iterable[BaseRequestParameterValidator]): A list of parameter validators.
    """

    def __init__(self, request_parameter_handlers: Iterable[BaseRequestParameterValidator]) -> None:
        self.request_parameter_handlers = request_parameter_handlers

    async def validate(self, request: Request) -> ValidateReturn:
        """Validates the request using the registered parameter validators.

        Args:
            request (Request): The incoming HTTP request.

        Returns:
            ValidateReturn: A tuple containing validated values and any validation errors.
        """
        values: Dict[str, Any] = {}
        errors: List[Dict[str, Any]] = []

        for param_handler in self.request_parameter_handlers:
            param_values, param_errors = await param_handler.validate(request)
            if param_errors:
                errors += param_errors
            else:
                values.update(cast(ResultValidate, param_values))  # if there's no error, there's a result

        return values, errors


class ResultValidator(Validator[Any]):
    """Validator for the result data.

    Validates the result of the handler's processing, typically before returning the response.

    Args:
        handler (Handler): The handler for the request.
        return_annotation (Optional[Type[Any]]): The annotation for the return type.
        response_type (Union[Type[Any], None, UnsetType]): The type of the response.
    """

    def __init__(
        self,
        handler: Handler,
        return_annotation: Type[Any] | None,
        *,
        response_type: Type[Any] | None | UnsetType,
    ) -> None:
        self._handler = handler

        if response_type is not Unset:
            return_annotation = response_type

        self._model_field = self._create_return_model(return_annotation)

    async def validate(self, data: Any) -> ValidateReturn:
        """Validates the data returned by the handler.

        Args:
            data (Any): The data to validate.

        Returns:
            ValidateReturn: A tuple containing validated data and any validation errors.
        """
        if self._model_field:
            return self._model_field.validate(data, {}, loc=(self._model_field.name,))
        return data, []

    def _create_return_model(self, annotation: Any) -> RapidyModelField | None:
        """Creates a model field based on the return annotation.

        Args:
            annotation (Any): The return annotation.

        Returns:
            Optional[RapidyModelField]: The created model field, or None if not applicable.
        """
        if annotation_is_stream_response(annotation) or is_empty(annotation):
            return None

        if is_union(annotation):
            union_annotations = get_args(annotation)
            annotation = Union[  # noqa: UP007
                tuple(annotation for annotation in union_annotations if not annotation_is_stream_response(annotation))
            ]

        return create_model_field_by_annotation(annotation)


def request_parameter_validator_factory(field_info: RequestParamFieldInfo) -> BaseRequestParameterValidator:
    """Creates a request parameter validator based on the field information.

    Args:
        field_info (RequestParamFieldInfo): The request parameter field information.

    Returns:
        BaseRequestParameterValidator: The appropriate request parameter validator.
    """
    extractor = get_extractor(field_info)

    if field_info.extract_single:
        return RequestSingleParameterValidator(extractor=extractor, http_request_param_type=field_info.param_type)

    return RequestAllDataParameterValidator(extractor=extractor, http_request_param_type=field_info.param_type)


def request_validator_factory(
    handler: Handler,
    request_params: List[HTTPRequestAttr],
) -> RequestValidator:
    """Creates a request validator based on the handler and request parameters.

    Args:
        handler (Handler): The handler for the request.
        request_params (List[HTTPRequestAttr]): The list of HTTP request attributes.

    Returns:
        RequestValidator: The created request validator.
    """
    parameter_extract_all: Dict[HTTPRequestParamType, bool] = {}
    param_validators: Dict[HTTPRequestParamType, BaseRequestParameterValidator] = {}

    for request_param in request_params:
        extract_all = not request_param.extract_as_single_param
        http_param_type = request_param.http_param_type

        already_defined_extract_all = parameter_extract_all.get(http_param_type)
        if already_defined_extract_all is not None:
            if (
                http_param_type == HTTPRequestParamType.body  # can't def two body
                or already_defined_extract_all != extract_all  # can't contain two types of extraction
            ):
                raise AnotherDataExtractionTypeAlreadyExistsError.create(
                    handler=handler,
                    attr_name=request_param.attribute_name,
                )

        else:
            parameter_extract_all[http_param_type] = extract_all

        request_parameter_validator = param_validators.get(http_param_type)
        if not request_parameter_validator:
            request_parameter_validator = request_parameter_validator_factory(request_param.field_info)
            param_validators[http_param_type] = request_parameter_validator

        request_parameter_validator.add_field(field_info=request_param.field_info, handler=handler)

    return RequestValidator(param_validators.values())


def result_validator_factory(
    handler: Handler,
    return_annotation: Type[Any] | None,
    response_type: Type[Any] | None | UnsetType,
) -> ResultValidator:
    """Creates a result validator for the handler's response.

    Args:
        handler (Handler): The handler for the request.
        return_annotation (Optional[Type[Any]]): The return type annotation.
        response_type (Union[Type[Any], None, UnsetType]): The type of the response.

    Returns:
        ResultValidator: The created result validator.
    """
    return ResultValidator(
        handler=handler,
        return_annotation=return_annotation,
        response_type=response_type,
    )
