from abc import ABC, abstractmethod
from types import FunctionType
from typing import Any, cast, Dict, List, Optional, Sequence, Tuple, Union

from aiohttp.web_request import Request
from typing_extensions import Annotated, Doc, TypeAlias

from rapidy._annotation_extractor import get_endpoint_handler_info
from rapidy._base_exceptions import RapidyHandlerException
from rapidy._client_errors import _regenerate_error_with_loc, RequiredFieldIsMissing
from rapidy._request_extractors import ExtractError, get_extractor
from rapidy._request_param_field_info import ParamFieldInfo
from rapidy._request_param_model_field import BaseModelField, create_param_model_field
from rapidy.request_enums import HTTPRequestParamType
from rapidy.typedefs import DictStrAny, ErrorWrapper, Middleware, ResultValidate, ValidateReturn
from rapidy.web_exceptions import HTTPValidationFailure

AttributeName: TypeAlias = str
AttributeValue: TypeAlias = Any

_Handler = Union[FunctionType, Middleware]


class AnotherDataExtractionTypeAlreadyExistsError(RapidyHandlerException):
    message = (
        'Attribute with this data extraction type cannot be added to the handler - '
        'another data extraction type is already use in handler.'
    )


class AttributeAlreadyExistsError(RapidyHandlerException):
    message = 'Attribute with this name or alias already exists.'


class HTTPRequestParameterHandler(ABC):
    def __init__(self, extractor: Any, http_request_param_type: HTTPRequestParamType) -> None:
        self._extractor = extractor
        self._http_request_param_type = http_request_param_type
        self._map_model_fields_by_alias: Dict[str, BaseModelField] = {}

    def add_field(self, field_info: ParamFieldInfo, handler: _Handler) -> None:
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
            required_fields_map: Dict[str, BaseModelField],
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
            required_fields_map: Dict[str, BaseModelField],
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
            required_fields_map: Dict[str, BaseModelField],
    ) -> ValidateReturn:
        model_field = list(required_fields_map.values())[0]

        rapid_param_type = cast(str, model_field.http_request_param_type)

        loc = (rapid_param_type,)

        validated_data, validated_errors = _validate_data_by_field(
            raw_data=raw_data,
            values={},
            loc=loc,
            model_field=model_field,
        )
        if validated_errors:
            return {}, validated_errors

        return {model_field.name: validated_data}, validated_errors


class HTTPRequestHandler:
    """The http request handler.

    This handler contains information about all parameters of the http-request
    that the endpoint is waiting for.
    """

    def __init__(
            self,
            request_attribute_name: Annotated[
                Optional[str],
                Doc(
                    """
                    The name of the handler attribute that expects the incoming `web.Request`.
                    """,
                ),
            ],
            request_parameter_handlers: Annotated[
                Sequence[HTTPRequestParameterHandler],
                Doc(
                    """
                    Sequence of http-parameter handlers that the endpoint expects.

                    min_len: 0
                    max_len: 5

                    Examples:
                        >>> []  # Endpoint does not expect incoming request data
                        >>> [headers, body]  # Endpoint expect only headers and body
                        >>> [path, headers, cookies, query_parameters, body]  # Endpoint expect full data
                    """,
                ),
            ],
    ) -> None:
        self.request_attribute_name = request_attribute_name
        self.request_parameter_handlers = request_parameter_handlers

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


def http_request_handler_builder(
        endpoint_handler: _Handler,
        request_attr_can_declare: bool = False,
) -> HTTPRequestHandler:
    request_attr_name, attr_fields_info = get_endpoint_handler_info(
        endpoint_handler=endpoint_handler, request_attr_can_declare=request_attr_can_declare,
    )

    request_parameter_handlers = create_http_request_parameter_handlers(
        endpoint_handler=endpoint_handler, attr_fields_info=attr_fields_info,
    )

    return HTTPRequestHandler(
        request_attribute_name=request_attr_name, request_parameter_handlers=request_parameter_handlers,
    )


def create_http_request_parameter_handlers(
        endpoint_handler: _Handler,
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
        model_field: BaseModelField,
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
        converted_errors = _regenerate_error_with_loc(errors=validated_errors, loc_prefix=())
        return values, converted_errors

    return validated_data, []
