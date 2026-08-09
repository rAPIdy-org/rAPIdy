from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import (
    fields as dataclass_fields,
    is_dataclass,
)
from functools import reduce
from importlib import import_module
from operator import or_
from typing import Any, cast, get_args, get_origin, get_type_hints, is_typeddict

from pydantic import BaseModel
from rapidy_core.annotation_checkers import is_empty, is_multi_value_annotation, is_union, lenient_issubclass
from rapidy_core.client_errors import ClientError
from rapidy_core.enums import HTTPRequestParamType
from rapidy_core.fields import create_model_field_by_annotation, RapidyModelField
from rapidy_core.parameters.http import RequestParamFieldInfo  # noqa: TC002 - runtime annotations

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.endpoint_handlers.http.annotation_checkers import annotation_is_stream_response
from rapidy.endpoint_handlers.http.attr_containers import HTTPRequestAttr
from rapidy.endpoint_handlers.http.fields import create_request_model_field, RequestModelField
from rapidy.endpoint_handlers.http.request.data_extractors import ExtractError, ExtractFunction
from rapidy.endpoint_handlers.validation import validate_data_by_model, Validator
from rapidy.request import Request
from rapidy.typedefs import Handler, UNSET, UnsetType, ValidateReturn

__all__ = (
    'AnotherDataExtractionTypeAlreadyExistsError',
    'AttributeAlreadyExistsError',
    'BaseRequestParameterValidator',
    'DuplicateParameterError',
    'RequestAllDataParameterValidator',
    'RequestSingleParameterValidator',
    'RequestValidator',
    'ResultValidator',
    'request_parameter_validator_factory',
    'request_validator_factory',
    'result_validator_factory',
)

_MAPPING_TYPE_ARGUMENTS = 2


class AnotherDataExtractionTypeAlreadyExistsError(RapidyHandlerException):
    """Raised when incompatible extraction modes share one source."""

    message = (
        'Attribute with this data extraction type cannot be added to the handler - '
        'another data extraction type is already use in handler.'
    )


class AttributeAlreadyExistsError(RapidyHandlerException):
    """Raised when a name or alias is registered twice."""

    message = 'Attribute with this name or alias already exists.'


class DuplicateParameterError(ClientError):
    """Reject repeated wire values for one scalar query or header field."""

    type = 'duplicate_parameter'
    msg_template = 'Multiple values are not allowed for scalar parameter {name!r}'


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
            if model_field.http_param_type in (HTTPRequestParamType.header, HTTPRequestParamType.query):
                raw_value, duplicate = _normalize_single_wire_value(raw_data, field_name, model_field)
                if duplicate:
                    errors.append(DuplicateParameterError(name=model_field.alias).get_error_info(loc=location))
                    continue
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
        if (
            model_field.need_validate
            and model_field.http_param_type in (HTTPRequestParamType.header, HTTPRequestParamType.query)
        ):
            raw_data, duplicate_errors = _normalize_container_wire_values(raw_data, model_field)
            if duplicate_errors:
                return {}, duplicate_errors
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


def _normalize_single_wire_value(
    raw_data: Any,
    field_name: str,
    model_field: RequestModelField,
) -> tuple[Any, bool]:
    values = _getall(raw_data, field_name)
    if values is None:
        return raw_data.get(field_name) if raw_data is not None else None, False
    if not values:
        return None, False
    if model_field.accepts_multiple_values:
        return values, False
    return values[0], len(values) > 1


def _normalize_container_wire_values(
    raw_data: Any,
    model_field: RequestModelField,
) -> tuple[Any, list[dict[str, Any]]]:
    if raw_data is None or not hasattr(raw_data, 'getall'):
        return raw_data, []
    headers = model_field.http_param_type == HTTPRequestParamType.header
    shapes, mapping_value_is_multiple = _container_shapes(model_field.type_, normalize_keys=headers)
    if shapes is None and mapping_value_is_multiple is None:
        return raw_data, []

    normalized: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_key in raw_data:
        lookup_key = str(raw_key).lower() if headers else str(raw_key)
        if lookup_key in seen:
            continue
        seen.add(lookup_key)
        shape = shapes.get(lookup_key) if shapes is not None else None
        if shape is None:
            output_key = str(raw_key)
            accepts_multiple = mapping_value_is_multiple
        else:
            output_key, accepts_multiple = shape
        values = _getall(raw_data, str(raw_key)) or []
        if accepts_multiple is True:
            normalized[output_key] = values
        elif len(values) <= 1 or (shape is None and mapping_value_is_multiple is None):
            normalized[output_key] = values[0] if values else None
        else:
            location = (model_field.http_param_type, output_key)
            errors.append(DuplicateParameterError(name=output_key).get_error_info(loc=location))
    return normalized, errors


def _container_shapes(
    annotation: Any,
    *,
    normalize_keys: bool,
) -> tuple[dict[str, tuple[str, bool]] | None, bool | None]:
    if lenient_issubclass(annotation, BaseModel):
        shapes: dict[str, tuple[str, bool]] = {}
        for name, field_info in annotation.model_fields.items():
            alias = field_info.validation_alias
            input_name = alias if isinstance(alias, str) else field_info.alias or name
            lookup_name = input_name.lower() if normalize_keys else input_name
            shapes[lookup_name] = (input_name, is_multi_value_annotation(field_info.annotation))
        return shapes, None
    if is_dataclass(annotation):
        resolved_annotations = get_type_hints(annotation, include_extras=True)
        shapes = {}
        for field_info in dataclass_fields(annotation):
            lookup_name = field_info.name.lower() if normalize_keys else field_info.name
            field_annotation = resolved_annotations.get(field_info.name, field_info.type)
            shapes[lookup_name] = (field_info.name, is_multi_value_annotation(field_annotation))
        return shapes, None
    if is_typeddict(annotation):
        annotations = get_type_hints(annotation, include_extras=True)
        shapes = {}
        for name, field_annotation in annotations.items():
            lookup_name = name.lower() if normalize_keys else name
            shapes[lookup_name] = (name, is_multi_value_annotation(field_annotation))
        return shapes, None

    origin = get_origin(annotation) or annotation
    if lenient_issubclass(origin, Mapping):
        args = get_args(annotation)
        value_annotation = args[1] if len(args) == _MAPPING_TYPE_ARGUMENTS else Any
        return {}, is_multi_value_annotation(value_annotation)
    return None, None


def _getall(raw_data: Any, key: str) -> list[Any] | None:
    getall = getattr(raw_data, 'getall', None)
    if getall is None:
        return None
    return list(getall(key, []))


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
        if response_type is not UNSET:
            return_annotation = response_type
        self._model_field = self._create_return_model(return_annotation)

    async def validate(self, data: Any) -> ValidateReturn:
        if self._model_field is not None:
            return self._model_field.validate(data, {}, loc=(self._model_field.name,))
        return data, []

    @property
    def has_response_contract(self) -> bool:
        """Return whether the handler declares a serializable response annotation."""
        return self._model_field is not None

    def serialize(
        self,
        data: Any,
        *,
        include: Any,
        exclude: Any,
        by_alias: bool,
        exclude_unset: bool,
        exclude_defaults: bool,
        exclude_none: bool,
        fallback: Callable[[Any], Any] | None,
    ) -> Any:
        """Serialize data through the declared response annotation."""
        if self._model_field is None:
            return data
        return self._model_field.serialize(
            data,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            fallback=fallback,
        )

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
