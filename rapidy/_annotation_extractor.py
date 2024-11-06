import inspect
from copy import deepcopy
from typing import Any, List, NamedTuple, Optional, Type

from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse
from typing_extensions import get_args

from rapidy._annotation_helpers import (
    annotation_is_annotated,
    annotation_is_optional,
    get_base_annotations,
    lenient_issubclass,
)
from rapidy._base_exceptions import RapidyHandlerException
from rapidy._constants import PYDANTIC_V1, PYDANTIC_V2
from rapidy._field_info import RapidyFieldInfo
from rapidy.request_parameters import ParamFieldInfo
from rapidy.typedefs import Handler, Required, Undefined


class NotRapidyParameterError(Exception):
    pass


class ParameterCannotUseDefaultError(RapidyHandlerException):
    message = 'Handler attribute with Type `{class_name}` cannot have a default value.'


class ParameterNotInstanceError(RapidyHandlerException):
    message = 'Rapidy parameter must be an instance.'


class ParameterCannotUseDefaultFactoryError(RapidyHandlerException):
    message = 'Handler attribute with Type `{class_name}` cannot have a default_factory.'


class SpecifyBothDefaultAndDefaultFactoryError(RapidyHandlerException):
    message = 'Cannot specify both default and default_factory in `{class_name}`.'


class ParameterCannotBeOptionalError(RapidyHandlerException):
    message = 'A parameter `{class_name}` cannot be optional.'


class SpecifyBothDefaultAndOptionalError(RapidyHandlerException):
    message = 'A parameter cannot be optional if it contains a default value in `{class_name}`.'


class SpecifyBothDefaultFactoryAndOptionalError(RapidyHandlerException):
    message = 'A parameter cannot be optional if it contains a default factory in `{class_name}`.'


class IncorrectDefineDefaultValueError(RapidyHandlerException):
    message = (
        'Default value cannot be set in `{class_name}`. '
        'You cannot specify a default value using Param(<default_value>, ...) and `=` at the same time.'
    )


class RequestFieldAlreadyExistsError(RapidyHandlerException):
    message = (
        'Error during attribute definition in the handler - request param defined twice.'
        'The error may be because the first attribute of the handler is not annotated.'
        'By default, `rAPIdy` will pass `web.Request` to the first attribute if it has no type annotation.'
    )


if PYDANTIC_V1:
    def copy_field_info(*, field_info: ParamFieldInfo, annotation: Any) -> ParamFieldInfo:
        return deepcopy(field_info)

elif PYDANTIC_V2:
    def copy_field_info(*, field_info: ParamFieldInfo, annotation: Any) -> ParamFieldInfo:  # noqa: F811 WPS440
        merged_field_info = type(field_info).from_annotation(annotation)
        copied_param_field_info = deepcopy(field_info)
        copied_param_field_info.metadata = merged_field_info.metadata
        copied_param_field_info.annotation = merged_field_info.annotation
        return copied_param_field_info
else:
    raise Exception


def prepare_field_info(
        attr_annotation: Any,
        attr_type_annotation: Any,
        attr_name: str,
        field_info: ParamFieldInfo,
) -> ParamFieldInfo:
    if attr_type_annotation is inspect.Signature.empty:
        attr_type_annotation = Any

    prepared_field_info = copy_field_info(field_info=field_info, annotation=attr_annotation)
    prepared_field_info.set_annotation(attr_type_annotation)
    prepared_field_info.set_attribute_name(attr_name)

    return prepared_field_info


def check_possibility_of_default(
        can_default: bool,
        default_exists: bool,
        default_is_none: bool,
        default_factory_exists: bool,
        param_is_optional: bool,
        handler: Handler,
        param: inspect.Parameter,
        field_info: ParamFieldInfo,
) -> None:
    if not can_default and param_is_optional:
        raise ParameterCannotBeOptionalError.create_with_handler_and_attr_info(
            handler=handler,
            attr_name=param.name,
            class_name=field_info.__class__.__name__,
        )

    if default_exists and not can_default:
        raise ParameterCannotUseDefaultError.create_with_handler_and_attr_info(
            handler=handler,
            attr_name=param.name,
            class_name=field_info.__class__.__name__,
        )

    if default_factory_exists and not can_default:
        raise ParameterCannotUseDefaultFactoryError.create_with_handler_and_attr_info(
            handler=handler,
            attr_name=param.name,
            class_name=field_info.__class__.__name__,
        )

    # NOTE: This error is caused earlier by `pydantic` for some scenarios.
    if default_exists and default_factory_exists:
        raise SpecifyBothDefaultAndDefaultFactoryError.create_with_handler_and_attr_info(
            handler=handler,
            attr_name=param.name,
            class_name=field_info.__class__.__name__,
        )

    if default_exists and not default_is_none and param_is_optional:
        raise SpecifyBothDefaultAndOptionalError.create_with_handler_and_attr_info(
            handler=handler,
            attr_name=param.name,
            class_name=field_info.__class__.__name__,
        )

    if default_factory_exists and param_is_optional:
        raise SpecifyBothDefaultFactoryAndOptionalError.create_with_handler_and_attr_info(
            handler=handler,
            attr_name=param.name,
            class_name=field_info.__class__.__name__,
        )


def get_annotated_definition_attr_default(
        param: inspect.Parameter,
        handler: Handler,
        type_: Any,
        field_info: ParamFieldInfo,
) -> Any:
    default_value_for_param_exists = param.default is not inspect.Signature.empty
    default_value_for_field_exists = check_default_value_for_field_exists(field_info)

    param_is_optional = annotation_is_optional(type_)

    default: Any = inspect.Signature.empty

    if default_value_for_param_exists:
        default = param.default

    elif default_value_for_field_exists:
        default = field_info.default

    elif param_is_optional:
        default = None

    check_possibility_of_default(
        can_default=field_info.can_default,
        default_exists=default_value_for_param_exists or default_value_for_field_exists,
        default_is_none=default is None,
        default_factory_exists=field_info.default_factory is not None,
        param_is_optional=param_is_optional,
        handler=handler,
        param=param,
        field_info=field_info,
    )

    if default_value_for_param_exists and default_value_for_field_exists:
        raise IncorrectDefineDefaultValueError.create_with_handler_and_attr_info(
            handler=handler,
            attr_name=param.name,
            class_name=field_info.__class__.__name__,
        )

    return default


def get_default_definition_attr_default(
        handler: Handler,
        type_: Any,
        param: inspect.Parameter,
        field_info: ParamFieldInfo,
) -> Any:
    param_is_optional = annotation_is_optional(type_)

    check_possibility_of_default(
        can_default=field_info.can_default,
        default_exists=check_default_value_for_field_exists(field_info),
        default_is_none=field_info.default is None,
        default_factory_exists=field_info.default_factory is not None,
        param_is_optional=param_is_optional,
        handler=handler,
        param=param,
        field_info=field_info,
    )

    if param_is_optional:
        return None

    return field_info.default


def check_default_value_for_field_exists(field_info: ParamFieldInfo) -> bool:
    return not (field_info.default is Undefined or field_info.default is Required)


def is_rapidy_param(type_: Any) -> bool:
    try:
        return isinstance(type_, ParamFieldInfo) and issubclass(type_.__class__, RapidyFieldInfo)
    except Exception:
        return False


def is_rapidy_type(type_: Any) -> bool:
    try:
        return isinstance(type_, type) and issubclass(type_, RapidyFieldInfo)
    except Exception:
        return False


def create_attribute_field_info(handler: Handler, param: inspect.Parameter) -> RapidyFieldInfo:
    attr_annotation = param.annotation
    attr_default = param.default
    attr_name = param.name

    if attr_default is not inspect.Signature.empty:
        if is_rapidy_param(attr_default):
            prepared_field_info = prepare_field_info(
                attr_annotation=attr_annotation,
                attr_type_annotation=attr_annotation,
                attr_name=attr_name,
                field_info=attr_default,
            )
            prepared_field_info.default = get_default_definition_attr_default(
                param=param, handler=handler, type_=attr_annotation, field_info=prepared_field_info,
            )
            return prepared_field_info

        elif is_rapidy_type(attr_default):
            raise ParameterNotInstanceError.create_with_handler_and_attr_info(handler=handler, attr_name=param.name)

    if annotation_is_annotated(attr_annotation):
        annotated_args = get_args(param.annotation)
        type_annotation = annotated_args[0]
        last_attr = annotated_args[-1]

        if not is_rapidy_param(last_attr):
            if is_rapidy_type(last_attr):
                raise ParameterNotInstanceError

            raise NotRapidyParameterError

        prepared_field_info = prepare_field_info(
            attr_annotation=attr_annotation,
            attr_type_annotation=type_annotation,
            attr_name=attr_name,
            field_info=last_attr,
        )
        prepared_field_info.default = get_annotated_definition_attr_default(
            param=param, handler=handler, type_=type_annotation, field_info=prepared_field_info,
        )

        return prepared_field_info

    raise NotRapidyParameterError


class EndpointHandlerInfo(NamedTuple):
    """Endpoint handler information.

    Attributes:
        request_attr_name:
            Name of the attribute expecting the incoming `web.Request`.
        response_attr_name:
            Name of the attribute expecting the current `web.Response`.
        attr_fields_info:
            Contains `ParamFieldInfo` for each attribute that can be processed by the Rapidy endpoint-handler.
        return_annotation:
            Handler return annotation.
    """

    request_attr_name: Optional[str]
    response_attr_name: Optional[str]
    attr_fields_info: List[ParamFieldInfo]
    return_annotation: Optional[Type[Any]]


def get_endpoint_handler_info(  # noqa: C901
        endpoint_handler: Handler,
        request_attr_can_declare: bool = False,
) -> EndpointHandlerInfo:
    """Extract annotation information from a handler function or view-handler method.

    Args:
        endpoint_handler:
            Endpoint handler for extracting annotation information.
            >>> def handler() -> web.Response: ... # <--- this object - handler

            >>> @routes.post('/')
            >>> def handler() -> web.Response: ... # <--- this object - handler

            >>> class Handler(web.View):
            >>>     def post(self) -> web.Response: ...  # <--- this object - post
        request_attr_can_declare:
            Flag that determines whether a handler in attributes can receive a `web.Request` injection.
            If `request_attr_can_declare=False` -> the example will not work.
            >>> def handler(request: web.Request) -> ...: ...  #  injection won't happen

    Raises:
        RequestFieldAlreadyExistsError: if two attr expecting to be injected by `web.Request`

    Returns:
        EndpointHandlerInfo - Endpoint handler information.

    Examples:
        >>> from rapidy import web

        >>> async def handler() -> web.Response:
        >>>     ...
        >>> get_endpoint_handler_info(handler)
        EndpointHandlerInfo(
            attr_fields_info=[],
            request_attr_name=None,
        )

        >>> async def handler(request) -> web.Response:
        >>>     ...
        >>> get_endpoint_handler_info(handler)
        EndpointHandlerInfo(
            attr_fields_info=[],
            request_attr_name='request',
        )

        >>> async def handler(f: str = web.Header()) -> web.Response:
        >>>     ...
        >>> get_endpoint_handler_info(handler)
        EndpointHandlerInfo(
            attr_fields_info=[ParamFieldInfo(http_request_param_type='header', ...)],
            request_attr_name=None,
        )

        >>> async def handler(
        >>>     f1: str = web.Body(),
        >>>     f2: str = web.Header(),
        >>>     f3: str = web.Header(),
        >>>     request_attr: web.Request,
        >>> ) -> web.Response:
        >>>    ...
        >>> get_endpoint_handler_info(handler)
        EndpointHandlerInfo(
            attr_fields_info=[
                ParamFieldInfo(http_request_param_type='header', ...),
                ParamFieldInfo(http_request_param_type='header', ...),
                ParamFieldInfo(http_request_param_type='body', ...),
            ],
            request_attr_name='request_attr',
        )
    """
    endpoint_signature = inspect.signature(endpoint_handler)
    signature_params = endpoint_signature.parameters
    return_annotation = endpoint_signature.return_annotation

    request_attr_name = None
    response_attr_name = None
    attr_fields_info: List[ParamFieldInfo] = []

    for param_name, param in signature_params.items():
        try:  # noqa: WPS229
            field_info = create_attribute_field_info(param=param, handler=endpoint_handler)
            attr_fields_info.append(field_info)
        except NotRapidyParameterError:
            # The block handles unknown attributes by extending the attribute injection logic.
            #
            # Currently, `rAPIdy` is only able to process two parameters
            # that are not related to `rAPIdy` validation logic
            # these are `web.Request` and `web.Response`.

            signature_index = list(signature_params.keys()).index(param_name)

            base_annotations = get_base_annotations(param.annotation)
            if len(base_annotations) > 1:
                # If there is more than one base attribute -> don't know what to do -> skip it.
                continue

            base_annotation = base_annotations[0]
            if request_attr_can_declare:  # Need to inject `web.Request` in a functional handler
                try:   # noqa: WPS505
                    type_is_request_subclass = issubclass(Request, base_annotation)
                except TypeError:
                    type_is_request_subclass = False

                if (
                    type_is_request_subclass
                    or base_annotation is inspect.Signature.empty and signature_index == 0
                ):  # If the first handler attribute is empty or the attribute contains the `web.Request` annotation
                    if request_attr_name is not None:  # protection against double injection of `web.Request`
                        raise RequestFieldAlreadyExistsError.create_with_handler_info(handler=endpoint_handler)

                    request_attr_name = param.name
                    continue

            if lenient_issubclass(base_annotation, StreamResponse):
                response_attr_name = param.name

    return EndpointHandlerInfo(
        request_attr_name=request_attr_name,
        response_attr_name=response_attr_name,
        attr_fields_info=attr_fields_info,
        return_annotation=return_annotation,
    )
