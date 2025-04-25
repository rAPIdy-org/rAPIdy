from __future__ import annotations

from typing import List

from attrs import define, Factory

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.annotation_checkers import is_empty, is_optional
from rapidy.endpoint_handlers.attr_containers import Attr
from rapidy.endpoint_handlers.attr_extractor import (
    CannotBeOptionalError,
    get_handler_raw_info,
    HandlerRawInfo,
    ParameterCannotUseDefaultError,
    ParameterCannotUseDefaultFactoryError,
)
from rapidy.endpoint_handlers.http.annotation_checkers import (
    annotation_is_request,
    annotation_is_stream_response,
    is_stream_reader,
)
from rapidy.endpoint_handlers.http.attr_containers import HTTPRequestAttr
from rapidy.enums import HTTPRequestParamType
from rapidy.parameters.http import RequestParamFieldInfo
from rapidy.typedefs import Handler, Undefined


class RequestFieldAlreadyExistsError(RapidyHandlerException):
    """Raised when a request parameter is defined twice in the handler's attributes.

    This error occurs when the first attribute of the handler is not annotated, and `rapidy`
    will automatically assign `web.Request` to the first attribute. The error indicates that
    the parameter has been defined more than once.
    """

    message = (
        'Error during attribute definition in the handler - request param defined twice. '
        'The error may be because the first attribute of the handler is not annotated. '
        'By default, `rapidy` will pass `web.Request` to the first attribute if it has no type annotation.'
    )


def raise_if_stream_reader_def_incorrectly(
    body_attr: HTTPRequestAttr,
    # only to create context with exception
    handler: Handler,
) -> None:
    """Raises an error if the stream reader definition is incorrect.

    This function checks whether the `body_attr` (which represents an HTTP request attribute)
    is defined incorrectly. The following conditions are checked:
    1. If the field is optional.
    2. If the field has a default value.
    3. If the field has a default factory.

    Args:
        body_attr (HTTPRequestAttr): The HTTP request attribute to check.
        handler (Handler): The handler that the attribute belongs to, used for exception context.

    Raises:
        CannotBeOptionalError: If the field is marked as optional.
        ParameterCannotUseDefaultError: If the field has a default value.
        ParameterCannotUseDefaultFactoryError: If the field has a default factory.
    """
    if is_optional(body_attr.field_annotation):
        raise CannotBeOptionalError.create(
            annotation=body_attr.attribute_annotation,
            class_name=body_attr.field_info.__class__.__name__,
            handler=handler,
            attr_name=body_attr.attribute_name,
        )

    if body_attr.field_info.default is not Undefined:
        raise ParameterCannotUseDefaultError.create(
            annotation=body_attr.attribute_annotation,
            class_name=body_attr.field_info.__class__.__name__,
            handler=handler,
            attr_name=body_attr.attribute_name,
        )

    if body_attr.field_info.default_factory is not None:
        raise ParameterCannotUseDefaultFactoryError.create(
            annotation=body_attr.attribute_annotation,
            class_name=body_attr.field_info.__class__.__name__,
            handler=handler,
            attr_name=body_attr.attribute_name,
        )


@define(slots=True)
class HTTPHandlerInfo(HandlerRawInfo):
    """Contains information about the HTTP handler attributes.

    This class extends `HandlerRawInfo` to add specific attributes related to the HTTP request
    and response, such as request parameters and request/response attributes.

    Attributes:
        request_attribute (Optional[Attr]): The attribute representing the HTTP request.
        response_attribute (Optional[Attr]): The attribute representing the HTTP response.
        request_params (List[HTTPRequestAttr]): A list of HTTP request parameters.
    """

    request_attribute: Attr | None = None
    response_attribute: Attr | None = None
    request_params: List[HTTPRequestAttr] = Factory(list)


def get_http_handler_info(
    handler: Handler,
    *,
    request_attr_can_declare_fst: bool,
) -> HTTPHandlerInfo:
    """Generates the HTTP handler information from the given handler.

    This function processes the handler to extract details about its request and response
    attributes, as well as the request parameters. It ensures that the handler's attributes
    are properly annotated and checks for potential errors (e.g., multiple definitions of
    `web.Request`).

    Args:
        handler (Handler): The handler to extract information from.
        request_attr_can_declare_fst (bool): Flag indicating whether the request attribute can be declared fst.

    Returns:
        HTTPHandlerInfo: The processed information about the HTTP handler, including its attributes
        and request parameters.

    Raises:
        RequestFieldAlreadyExistsError: If the request field is defined more than once.
    """
    handler_raw_info = get_handler_raw_info(handler=handler)

    http_handler_info = HTTPHandlerInfo(
        return_annotation=handler_raw_info.return_annotation,
        attrs=handler_raw_info.attrs,
        data_attrs=handler_raw_info.data_attrs,
    )

    for rapidy_attr in handler_raw_info.data_attrs:
        if isinstance(rapidy_attr.field_info, RequestParamFieldInfo):
            http_attr = HTTPRequestAttr.create_by_data_attr(rapidy_attr)

            if http_attr.http_param_type == HTTPRequestParamType.body and is_stream_reader(
                http_attr.field_annotation,
                can_optional=True,
            ):
                raise_if_stream_reader_def_incorrectly(body_attr=http_attr, handler=handler)

            http_handler_info.request_params.append(http_attr)

    for additional_attr in handler_raw_info.attrs:
        if annotation_is_stream_response(additional_attr.attribute_annotation):
            http_handler_info.response_attribute = additional_attr

        # If the first handler attribute is empty or the attribute contains the `web.Request` annotation
        elif annotation_is_request(additional_attr.attribute_annotation) or (
            request_attr_can_declare_fst
            and (is_empty(additional_attr.attribute_annotation) and additional_attr.attribute_idx == 0)
        ):
            # protection against double injection of `web.Request`
            if http_handler_info.request_attribute:
                raise RequestFieldAlreadyExistsError.create(handler=handler)

            http_handler_info.request_attribute = additional_attr

    return http_handler_info
