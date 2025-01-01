import inspect
from abc import ABC, abstractmethod
from dataclasses import is_dataclass
from typing import Any, cast, Dict, get_args, Iterable, List, Mapping, Optional, Type, Union

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
from rapidy.typedefs import Handler, ResultValidate, Unset, ValidateReturn
from rapidy.web_request import Request


class AnotherDataExtractionTypeAlreadyExistsError(RapidyHandlerException):
    message = (
        'Attribute with this data extraction type cannot be added to the handler - '
        'another data extraction type is already use in handler.'
    )


class AttributeAlreadyExistsError(RapidyHandlerException):
    message = 'Attribute with this name or alias already exists.'


class BaseRequestValidator(Validator[Request], ABC):
    pass


class BaseRequestParameterValidator(BaseRequestValidator, ABC):
    def __init__(self, extractor: Any, http_request_param_type: HTTPRequestParamType) -> None:
        self._extractor = extractor
        self._http_request_param_type = http_request_param_type
        self._map_model_fields_by_alias: Dict[str, RequestModelField] = {}

    async def validate(self, request: Request) -> ValidateReturn:
        try:
            raw_data = await self._extract_raw_data(request)
        except ExtractError as exc:
            return {}, [exc.get_error_info(loc=(self._http_request_param_type,))]

        return await self._get_validated_data(raw_data=raw_data, required_fields_map=self._map_model_fields_by_alias)

    def add_field(self, field_info: RequestParamFieldInfo, handler: Handler) -> None:
        model_field = create_request_model_field(field_info=field_info)
        extraction_name = model_field.alias or model_field.name

        if self._map_model_fields_by_alias.get(extraction_name):
            raise AttributeAlreadyExistsError.create(handler=handler, attr_name=field_info.name)

        self._map_model_fields_by_alias[extraction_name] = model_field

    async def _extract_raw_data(self, request: Request) -> Any:
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
        raise NotImplementedError


class RequestSingleParameterValidator(BaseRequestParameterValidator):
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
    async def _get_validated_data(
        self,
        raw_data: Any,
        required_fields_map: Dict[str, RequestModelField],
    ) -> ValidateReturn:
        model_field = list(required_fields_map.values())[0]  # noqa: RUF015

        if is_dataclass(model_field.type_) and isinstance(raw_data, (MultiDict, MultiDictProxy, Mapping)):
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
        dataclass_attrs = inspect.signature(model_field_type).parameters.keys()
        return {attr_name: current_raw.get(attr_name) for attr_name in dataclass_attrs if attr_name in current_raw}


class RequestValidator(BaseRequestValidator):
    def __init__(self, request_parameter_handlers: Iterable[BaseRequestParameterValidator]) -> None:
        self.request_parameter_handlers = request_parameter_handlers

    async def validate(self, request: Request) -> ValidateReturn:
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
    def __init__(
        self,
        handler: Handler,
        return_annotation: Optional[Type[Any]],
        *,
        response_type: Optional[Type[Any]],
    ) -> None:
        self._handler = handler

        if response_type is not Unset:
            return_annotation = response_type

        self._model_field = self._create_return_model(return_annotation)

    async def validate(self, data: Any) -> ValidateReturn:
        if self._model_field:
            return self._model_field.validate(data, {}, loc=(self._model_field.name,))
        return data, []

    def _create_return_model(self, annotation: Any) -> Optional[RapidyModelField]:
        if annotation_is_stream_response(annotation) or is_empty(annotation):
            return None

        if is_union(annotation):
            union_annotations = get_args(annotation)
            annotation = Union[
                tuple(annotation for annotation in union_annotations if not annotation_is_stream_response(annotation))
            ]

        return create_model_field_by_annotation(annotation)


def request_parameter_validator_factory(field_info: RequestParamFieldInfo) -> BaseRequestParameterValidator:
    extractor = get_extractor(field_info)

    if field_info.extract_single:
        return RequestSingleParameterValidator(extractor=extractor, http_request_param_type=field_info.param_type)

    return RequestAllDataParameterValidator(extractor=extractor, http_request_param_type=field_info.param_type)


def request_validator_factory(
    handler: Handler,
    request_params: List[HTTPRequestAttr],
) -> RequestValidator:
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
    return_annotation: Optional[Type[Any]],
    response_type: Optional[Union[Type[Any]]],
) -> ResultValidator:
    return ResultValidator(
        handler=handler,
        return_annotation=return_annotation,
        response_type=response_type,
    )
