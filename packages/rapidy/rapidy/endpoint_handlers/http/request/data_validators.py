from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import is_dataclass
from functools import reduce
from importlib import import_module
from operator import or_
from typing import Any, cast, get_args, TYPE_CHECKING

from rapidy_core.annotation_checkers import is_empty, is_union
from rapidy_core.enums import HTTPRequestParamType
from rapidy_core.fields import create_model_field_by_annotation, RapidyModelField

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.endpoint_handlers.http.annotation_checkers import annotation_is_stream_response
from rapidy.endpoint_handlers.http.attr_containers import HTTPRequestAttr
from rapidy.endpoint_handlers.http.fields import create_request_model_field, RequestModelField
from rapidy.endpoint_handlers.http.request.data_extractors import ExtractError, ExtractFunction
from rapidy.endpoint_handlers.validation import validate_data_by_model, Validator
from rapidy.request import Request
from rapidy.typedefs import Handler, Unset, UnsetType, ValidateReturn

if TYPE_CHECKING:
    from rapidy_core.parameters.http import RequestParamFieldInfo

__all__ = (
    'AnotherDataExtractionTypeAlreadyExistsError',
    'AttributeAlreadyExistsError',
    'BaseRequestParameterValidator',
    'RequestAllDataParameterValidator',
    'RequestSingleParameterValidator',
    'RequestValidator',
    'ResultValidator',
    'request_parameter_validator_factory',
    'request_validator_factory',
    'result_validator_factory',
)


class AnotherDataExtractionTypeAlreadyExistsError(RapidyHandlerException):
    """Raised when incompatible extraction modes share one source."""

    message = (
        'Attribute with this data extraction type cannot be added to the handler - '
        'another data extraction type is already use in handler.'
    )


class AttributeAlreadyExistsError(RapidyHandlerException):
    """Raised when a name or alias is registered twice."""

    message = 'Attribute with this name or alias already exists.'


class BaseRequestValidator(Validator[Request], ABC):
    """Base class for request validators."""


class BaseRequestParameterValidator(BaseRequestValidator, ABC):
    """Extract and validate fields belonging to one request source."""

    def __init__(self, extractor: ExtractFunction, http_request_param_type: HTTPRequestParamType) -> None:
        self._extractor = extractor
        self._http_request_param_type = http_request_param_type
        self._map_model_fields_by_alias: dict[str, RequestModelField] = {}

    async def validate(self, request: Request) -> ValidateReturn:
        try:
            raw_data = await self._extract_raw_data(request)
        except ExtractError as exc:
            return {}, [exc.get_error_info(loc=(self._http_request_param_type,))]
        return await self._get_validated_data(raw_data, self._map_model_fields_by_alias)

    def add_field(self, field_info: RequestParamFieldInfo, handler: Handler) -> None:
        model_field = create_request_model_field(field_info)
        extraction_name = model_field.alias
        if extraction_name in self._map_model_fields_by_alias:
            raise AttributeAlreadyExistsError.create(handler=handler, attr_name=field_info.name)
        self._map_model_fields_by_alias[extraction_name] = model_field

    async def _extract_raw_data(self, request: Request) -> Any:
        cache = getattr(request, '_cache', None)
        if cache is not None and self._http_request_param_type in cache:
            return cache[self._http_request_param_type]

        raw_data = await self._extractor(request)
        if cache is not None:
            cache[self._http_request_param_type] = raw_data
        return raw_data

    @abstractmethod
    async def _get_validated_data(
        self,
        raw_data: Any,
        required_fields_map: dict[str, RequestModelField],
    ) -> ValidateReturn:
        raise NotImplementedError


class RequestSingleParameterValidator(BaseRequestParameterValidator):
    """Validate individually addressed source values."""

    async def _get_validated_data(
        self,
        raw_data: Any,
        required_fields_map: dict[str, RequestModelField],
    ) -> ValidateReturn:
        values: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []
        for field_name, model_field in required_fields_map.items():
            location = (model_field.http_param_type, model_field.alias)
            raw_value = raw_data.get(field_name) if raw_data is not None else None
            value, field_errors = validate_data_by_model(
                model_field,
                raw_data=raw_value,
                values=values,
                loc=location,
            )
            if field_errors:
                errors.extend(field_errors)
            else:
                values[model_field.name] = value
        return values, errors


class RequestAllDataParameterValidator(BaseRequestParameterValidator):
    """Validate one marker representing an entire request source."""

    async def _get_validated_data(
        self,
        raw_data: Any,
        required_fields_map: dict[str, RequestModelField],
    ) -> ValidateReturn:
        model_field = next(iter(required_fields_map.values()))
        if is_dataclass(model_field.type_) and isinstance(raw_data, Mapping):
            raw_data = self._create_dataclass_raw_data(raw_data, model_field.type_)

        value, errors = validate_data_by_model(
            model_field,
            raw_data=raw_data,
            values={},
            loc=(model_field.http_param_type,),
        )
        if errors:
            return {}, errors
        return {model_field.name: value}, []

    @staticmethod
    def _create_dataclass_raw_data(current_raw: Mapping[str, Any], model_field_type: Any) -> dict[str, Any]:
        names = inspect.signature(model_field_type).parameters
        return {name: current_raw.get(name) for name in names if name in current_raw}


class RequestValidator(BaseRequestValidator):
    """Combine validators for all request sources."""

    def __init__(self, request_parameter_handlers: Iterable[BaseRequestParameterValidator]) -> None:
        self.request_parameter_handlers = tuple(request_parameter_handlers)

    async def validate(self, request: Request) -> ValidateReturn:
        values: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []
        for validator in self.request_parameter_handlers:
            current_values, current_errors = await validator.validate(request)
            if current_errors:
                errors.extend(current_errors)
            elif current_values:
                values.update(current_values)
        return values, errors


class ResultValidator(Validator[Any]):
    """Validate a handler result from its return contract."""

    def __init__(
        self,
        handler: Handler,
        return_annotation: type[Any] | None,
        *,
        response_type: type[Any] | UnsetType | None,
    ) -> None:
        self._handler = handler
        if response_type is not Unset:
            return_annotation = response_type
        self._model_field = self._create_return_model(return_annotation)

    async def validate(self, data: Any) -> ValidateReturn:
        if self._model_field is not None:
            return self._model_field.validate(data, {}, loc=(self._model_field.name,))
        return data, []

    @staticmethod
    def _create_return_model(annotation: Any) -> RapidyModelField | None:
        if annotation_is_stream_response(annotation) or is_empty(annotation):
            return None
        if is_union(annotation):
            filtered = tuple(item for item in get_args(annotation) if not annotation_is_stream_response(item))
            if not filtered:
                return None
            annotation = reduce(or_, filtered)
        return create_model_field_by_annotation(annotation)


def request_parameter_validator_factory(field_info: RequestParamFieldInfo) -> BaseRequestParameterValidator:
    """Create a source validator once milestone 06 installs wire extractors."""
    module = import_module('rapidy.endpoint_handlers.http.request.data_extractors')
    get_extractor = cast('Callable[[RequestParamFieldInfo], ExtractFunction]', module.__dict__['get_extractor'])
    extractor = get_extractor(field_info)
    validator_type = RequestSingleParameterValidator if field_info.extract_single else RequestAllDataParameterValidator
    return validator_type(extractor=extractor, http_request_param_type=field_info.param_type)


def request_validator_factory(handler: Handler, request_params: list[HTTPRequestAttr]) -> RequestValidator:
    """Group prepared request markers by source and extraction mode."""
    extract_all_by_type: dict[HTTPRequestParamType, bool] = {}
    validators: dict[HTTPRequestParamType, BaseRequestParameterValidator] = {}

    for request_param in request_params:
        extract_all = not request_param.extract_as_single_param
        param_type = request_param.http_param_type
        existing_mode = extract_all_by_type.get(param_type)
        if existing_mode is not None and (param_type == HTTPRequestParamType.body or existing_mode != extract_all):
            raise AnotherDataExtractionTypeAlreadyExistsError.create(
                handler=handler,
                attr_name=request_param.attribute_name,
            )
        extract_all_by_type[param_type] = extract_all

        validator = validators.get(param_type)
        if validator is None:
            validator = request_parameter_validator_factory(request_param.field_info)
            validators[param_type] = validator
        validator.add_field(request_param.field_info, handler)

    return RequestValidator(validators.values())


def result_validator_factory(
    handler: Handler,
    return_annotation: type[Any] | None,
    response_type: type[Any] | UnsetType | None,
) -> ResultValidator:
    """Create a shared-core-backed handler result validator."""
    return ResultValidator(handler, return_annotation, response_type=response_type)
