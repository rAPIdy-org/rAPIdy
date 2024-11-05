import inspect
from abc import ABC, abstractmethod
from concurrent.futures import Executor
from dataclasses import is_dataclass
from pprint import pformat
from typing import Any, cast, Dict, List, Mapping, Optional, Sequence, Tuple, Type, Union

from aiohttp.helpers import sentinel
from aiohttp.typedefs import JSONEncoder
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
from multidict import MultiDict, MultiDictProxy
from typing_extensions import get_args, TypeAlias, TypeVar

from rapidy._annotation_extractor import get_endpoint_handler_info
from rapidy._annotation_helpers import annotation_is_union, lenient_issubclass
from rapidy._base_exceptions import RapidyHandlerException
from rapidy._client_errors import normalize_errors, regenerate_error_with_loc, RequiredFieldIsMissing
from rapidy._endpoint_helpers import create_response
from rapidy._endpoint_model_field import (
    BaseRequestModelField,
    create_param_model_field,
    create_response_model_field,
    ModelField,
)
from rapidy._request_extractors import ExtractError, get_extractor
from rapidy._request_param_field_info import ParamFieldInfo
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import ContentType, HTTPRequestParamType
from rapidy.typedefs import DictStrAny, ErrorWrapper, Handler, ResultValidate, ValidateReturn, ValidationErrorList
from rapidy.web_exceptions import HTTPValidationFailure

TResponse = TypeVar('TResponse', bound=StreamResponse)

AttributeName: TypeAlias = str
AttributeValue: TypeAlias = Any


class AnotherDataExtractionTypeAlreadyExistsError(RapidyHandlerException):
    message = (
        'Attribute with this data extraction type cannot be added to the handler - '
        'another data extraction type is already use in handler.'
    )


class AttributeAlreadyExistsError(RapidyHandlerException):
    message = 'Attribute with this name or alias already exists.'


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
        return ResponseValidationError.create_with_handler_info(
            handler, errors=pformat(normalize_errors(errors)), **format_fields,
        )


class MissingContentTypeHeader(RapidyHandlerException):
    message = 'The server response does not contain a `Content-Type` header'


class HTTPRequestParameterHandler(ABC):
    def __init__(self, extractor: Any, http_request_param_type: HTTPRequestParamType) -> None:
        self._extractor = extractor
        self._http_request_param_type = http_request_param_type
        self._map_model_fields_by_alias: Dict[str, BaseRequestModelField] = {}

    def add_field(self, field_info: ParamFieldInfo, handler: Handler) -> None:
        model_field = create_param_model_field(field_info=field_info)
        extraction_name = model_field.alias or model_field.name

        if self._map_model_fields_by_alias.get(extraction_name):
            raise AttributeAlreadyExistsError.create_with_handler_and_attr_info(
                handler=handler, attr_name=field_info.attribute_name,
            )

        self._map_model_fields_by_alias[extraction_name] = model_field

    async def validate_parameter_data(self, request: Request) -> ValidateReturn:
        try:
            raw_data = await self._extract_raw_data(request)
        except ExtractError as exc:
            return {}, [exc.get_error_info(loc=(self._http_request_param_type,))]

        return await self._get_validated_data(raw_data=raw_data, required_fields_map=self._map_model_fields_by_alias)

    @abstractmethod
    async def _get_validated_data(
            self,
            raw_data: Any,
            required_fields_map: Dict[str, BaseRequestModelField],
    ) -> ValidateReturn:
        raise NotImplementedError

    async def _extract_raw_data(self, request: Request) -> Any:
        raw_data = request._cache.get(self._http_request_param_type)

        if not raw_data:
            raw_data = await self._extractor(request)
            request._cache[self._http_request_param_type] = raw_data

        return raw_data


class SingleKeyHandler(HTTPRequestParameterHandler):
    async def _get_validated_data(
            self,
            raw_data: Any,
            required_fields_map: Dict[str, BaseRequestModelField],
    ) -> ValidateReturn:
        all_validated_values: Dict[str, Any] = {}
        all_validated_errors: List[Dict[str, Any]] = []

        for required_field_name, model_field in required_fields_map.items():  # noqa: WPS440
            loc = (model_field.http_request_param_type, model_field.alias)
            raw_param_data = raw_data.get(required_field_name) if raw_data is not None else None

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


class AllDataHandler(HTTPRequestParameterHandler):
    async def _get_validated_data(
            self,
            raw_data: Any,
            required_fields_map: Dict[str, BaseRequestModelField],
    ) -> ValidateReturn:
        model_field = list(required_fields_map.values())[0]

        rapid_param_type = cast(str, model_field.http_request_param_type)

        loc = (rapid_param_type,)

        if is_dataclass(model_field.type_) and isinstance(raw_data, (MultiDict, MultiDictProxy, Mapping)):
            raw_data = self._create_dataclass_raw_data_by_multidict(raw_data, model_field_type=model_field.type_)

        validated_data, validated_errors = _validate_data_by_field(
            raw_data=raw_data,
            values={},
            loc=loc,
            model_field=model_field,
        )
        if validated_errors:
            return {}, validated_errors

        return {model_field.name: validated_data}, validated_errors

    def _create_dataclass_raw_data_by_multidict(
            self,
            current_raw: Any,
            *,
            model_field_type: Type[Any],
    ) -> Dict[str, Any]:
        dataclass_attrs = inspect.signature(model_field_type).parameters.keys()
        return {
            attr_name: current_raw.get(attr_name)
            for attr_name in dataclass_attrs
            if attr_name in current_raw
        }


class HTTPResponseHandler:
    def __init__(
            self,
            endpoint_handler: Handler,
            return_annotation: Optional[Type[Any]],
            *,
            validate: bool,
            response_type: Optional[Type[Any]],  # must be - aiohttp.helpers.sentinel by default
            response_content_type: Union[str, ContentType, None],
            charset: str,
            zlib_executor: Optional[Executor],
            zlib_executor_size: Optional[int],
            # json preparer
            include_fields: Optional[Include],
            exclude_fields: Optional[Exclude],
            by_alias: bool,
            exclude_unset: bool,
            exclude_defaults: bool,
            exclude_none: bool,
            custom_encoder: Optional[CustomEncoder],
            json_encoder: JSONEncoder,
    ) -> None:
        """Create rAPIdy HTTPResponseHandler instance.

        Args:
            endpoint_handler:
                Endpoint handler for extracting annotation information.
                >>> def handler() -> web.Response: ... # <--- this object - handler

                >>> @routes.post('/')
                >>> def handler() -> web.Response: ... # <--- this object - handler

                >>> class Handler(web.View):
                >>>     def post(self) -> web.Response: ...  # <--- this object - post
            return_annotation:
                Handler return annotation.
                This attribute is used to create the response model.
                if the `response_type` attribute is defined, the response model will not be created.
                >>> def handler(
                >>>     # ...
                >>> ) -> web.Response: # <--- this
            validate:
                The flag determines whether to validate the handler response.
            response_type:
                Handler response type.
                This attribute is used to create the response model.
                If this attribute is defined, it overrides the `return_annotation` attribute logic.
            response_content_type:
                Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
            charset:
                The `charset` that will be used to encode and decode handler result data.
            zlib_executor:
                Executor to use for zlib compression
            zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            include_fields:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            exclude_fields:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True
        """
        self._handler = endpoint_handler
        self._model_field = None

        if validate:
            if response_type is not sentinel:
                return_annotation = response_type

            if return_annotation is not inspect.Signature.empty:
                if annotation_is_union(return_annotation):
                    union_annotations = get_args(return_annotation)
                    return_annotation = Union[  # type: ignore[assignment]
                        tuple(
                            annotation for annotation in union_annotations  # noqa: WPS361
                            if not lenient_issubclass(annotation, StreamResponse)
                        )
                    ]
                    self._model_field = create_response_model_field(type_=return_annotation)

                elif not lenient_issubclass(return_annotation, StreamResponse):
                    self._model_field = create_response_model_field(type_=return_annotation)

        self._response_content_type = response_content_type
        self._charset = charset
        self._zlib_executor = zlib_executor
        self._zlib_executor_size = zlib_executor_size
        self._json_encoder = json_encoder

        self._include_fields = include_fields
        self._exclude_fields = exclude_fields
        self._by_alias = by_alias
        self._exclude_unset = exclude_unset
        self._exclude_defaults = exclude_defaults
        self._exclude_none = exclude_none
        self._custom_encoder = custom_encoder

    def validate(self, handler_result: Any, current_response: Optional[Response]) -> StreamResponse:
        if lenient_issubclass(type(handler_result), StreamResponse):
            return handler_result

        if self._model_field:
            handler_result = self._validate(handler_result, model_field=self._model_field)

        if current_response is None:
            current_response = create_response(
                content_type=self._response_content_type,
                charset=self._charset,
                zlib_executor=self._zlib_executor,
                zlib_executor_size=self._zlib_executor_size,
                include=self._include_fields,
                exclude=self._exclude_fields,
                by_alias=self._by_alias,
                exclude_unset=self._exclude_unset,
                exclude_defaults=self._exclude_defaults,
                exclude_none=self._exclude_none,
                custom_encoder=self._custom_encoder,
                json_encoder=self._json_encoder,
            )

        if handler_result is None:
            return current_response

        current_response.body = handler_result
        return current_response

    def _validate(self, handler_result: Any, model_field: ModelField) -> Any:
        handler_result, validated_errors = model_field.validate(
            handler_result, {}, loc=(model_field.name,),
        )
        if validated_errors:
            raise ResponseValidationError.create_with_handler_validation_errors(
                handler=self._handler, errors=validated_errors,
            )
        return handler_result


class EndpointHandler:
    """The endpoint handler.

    EndpointHandler contains information about:
     - all parameters of the http request that the endpoint is expecting
     - endpoint response type

    EndpointHandler validate the incoming request and the endpoint response.

    Attributes:
        request_attribute_name:
            The name of the handler attribute that expecting the incoming `web.Request`
        response_attribute_name:
            The name of the handler attribute that expecting the current `web.Response`.
        request_parameter_handlers:
            Sequence of http-parameter handlers that the endpoint expects. Len: 0-5.
            >>> request_parameter_handlers=[]  # Endpoint does not expect incoming request data
            >>> request_parameter_handlers=[headers, body]  # Endpoint expect only headers and body
            >>> request_parameter_handlers=[path, headers, cookies, query_parameters, body]  # Endpoint expect full data
        response_handler:
            Handler of a HTTP response.
    """

    __slots__ = 'request_attribute_name', 'response_attribute_name', 'request_parameter_handlers', 'response_handler'

    def __init__(
            self,
            request_attribute_name: Optional[str],
            response_attribute_name: Optional[str],
            request_parameter_handlers: Sequence[HTTPRequestParameterHandler],
            response_handler: HTTPResponseHandler,
    ) -> None:
        self.request_attribute_name = request_attribute_name
        self.response_attribute_name = response_attribute_name
        self.request_parameter_handlers = request_parameter_handlers
        self.response_handler = response_handler

    async def validate_request(self, request: Request) -> Dict[AttributeName, AttributeValue]:
        """Check the incoming request for errors.

        Raises:
             HTTPValidationFailure: If the request is invalid.
        """
        values: Dict[str, Any] = {}
        errors: List[Dict[str, Any]] = []

        for param_handler in self.request_parameter_handlers:
            param_values, param_errors = await param_handler.validate_parameter_data(request)
            if param_errors:
                errors += param_errors
            else:
                values.update(cast(ResultValidate, param_values))  # if there's no error, there's a result

        if errors:
            raise HTTPValidationFailure(errors=errors)

        return values

    def validate_response(self, response: Any, current_response: Optional[Response]) -> StreamResponse:
        return self.response_handler.validate(response, current_response)


def endpoint_handler_builder(
        endpoint_handler: Handler,
        *,
        request_attr_can_declare: bool = False,
        # response
        response_validate: bool,
        response_type: Optional[Type[Any]],
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
) -> EndpointHandler:
    request_attr_name, response_attr_name, attr_fields_info, return_annotation = get_endpoint_handler_info(
        endpoint_handler=endpoint_handler, request_attr_can_declare=request_attr_can_declare,
    )

    request_parameter_handlers = create_http_request_parameter_handlers(
        endpoint_handler=endpoint_handler, attr_fields_info=attr_fields_info,
    )

    response_handler = HTTPResponseHandler(
        endpoint_handler=endpoint_handler,
        return_annotation=return_annotation,
        validate=response_validate,
        response_type=response_type,
        response_content_type=response_content_type,
        charset=response_charset,
        zlib_executor=response_zlib_executor,
        zlib_executor_size=response_zlib_executor_size,
        include_fields=response_include_fields,
        exclude_fields=response_exclude_fields,
        by_alias=response_by_alias,
        exclude_unset=response_exclude_unset,
        exclude_defaults=response_exclude_defaults,
        exclude_none=response_exclude_none,
        custom_encoder=response_custom_encoder,
        json_encoder=response_json_encoder,
    )

    return EndpointHandler(
        request_attribute_name=request_attr_name,
        response_attribute_name=response_attr_name,
        request_parameter_handlers=request_parameter_handlers,
        response_handler=response_handler,
    )


def create_http_request_parameter_handlers(
        endpoint_handler: Handler,
        attr_fields_info: List[ParamFieldInfo],
) -> List[HTTPRequestParameterHandler]:
    parameter_extract_all: Dict[HTTPRequestParamType, bool] = {}
    param_containers: Dict[HTTPRequestParamType, HTTPRequestParameterHandler] = {}

    for field_info in attr_fields_info:
        http_request_param_type: HTTPRequestParamType = field_info.http_request_param_type

        already_defined_extract_all = parameter_extract_all.get(http_request_param_type)
        if already_defined_extract_all is not None:
            if (
                field_info.http_request_param_type == HTTPRequestParamType.body  # can't def two body
                or already_defined_extract_all != field_info.extract_all  # can't contain two types of extraction
            ):
                raise AnotherDataExtractionTypeAlreadyExistsError.create_with_handler_and_attr_info(
                    handler=endpoint_handler, attr_name=field_info.attribute_name,
                )

        else:
            parameter_extract_all[field_info.http_request_param_type] = field_info.extract_all

        param_container = param_containers.get(http_request_param_type)
        if not param_container:
            param_container = create_parameter_handler(field_info=field_info)
            param_containers[field_info.http_request_param_type] = param_container

        param_container.add_field(field_info=field_info, handler=endpoint_handler)

    return list(param_containers.values())


def create_parameter_handler(field_info: ParamFieldInfo) -> HTTPRequestParameterHandler:
    http_request_param_type = field_info.http_request_param_type

    extractor = get_extractor(field_info)

    if field_info.extract_all:
        return AllDataHandler(extractor=extractor, http_request_param_type=http_request_param_type)

    return SingleKeyHandler(extractor=extractor, http_request_param_type=http_request_param_type)


def _validate_data_by_field(  # noqa: WPS212
        raw_data: Any,
        loc: Tuple[str, ...],
        model_field: BaseRequestModelField,
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
        converted_errors = regenerate_error_with_loc(errors=validated_errors, loc_prefix=())
        return values, converted_errors

    return validated_data, []
