from __future__ import annotations

from concurrent.futures import Executor
from functools import wraps
from http import HTTPStatus
from typing import Any, cast, TYPE_CHECKING

from rapidy_core.enums import HTTPMethod

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.depends import inject_http
from rapidy.endpoint_handlers.http.controller import controller_factory
from rapidy.exceptions import HTTPMethodNotAllowed
from rapidy.request import Request
from rapidy.response import Response, StreamResponse
from rapidy.routing.http.helper_types import HandlerPartial
from rapidy.typedefs import Handler, JSONEncoder, View

if TYPE_CHECKING:
    from rapidy_core.encoders import CustomEncoder, Exclude, Include
    from rapidy_core.enums import Charset, ContentType

__all__ = (
    'METH_ALL',
    'AllowHeadError',
    'MethodAlreadyRegisteredError',
    'MethodNotFoundInViewError',
    'handler_validation_wrapper',
    'view_validation_wrapper',
)

METH_ALL = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}


class AllowHeadError(RapidyHandlerException):
    """Raised when a View cannot derive HEAD from a missing GET method."""

    message = (
        'Cannot automatically define the `head` method in `View` because the `get` method is not defined.'
        '\nThis is internal `rAPIdy` error, please open the issue - '
        'https://github.com/rAPIdy-org/rAPIdy/issues/new'
    )


class MethodNotFoundInViewError(RapidyHandlerException):
    """Raised when a requested View method is absent."""

    message = 'Failed to register View - method named `{method_name}` was not found.'


class MethodAlreadyRegisteredError(ValueError):
    """Raised when a View method is registered more than once."""


def _di_wrap(handler: Handler) -> Handler:
    """Bind HTTP dependency injection before request validation."""
    return inject_http(handler)


def _create_pre_response(
    *,
    status_code: HTTPStatus,
    response_content_type: str | ContentType | None,
    response_charset: str | Charset,
    response_zlib_executor: Executor | None,
    response_zlib_executor_size: int | None,
    response_include_fields: Include | None,
    response_exclude_fields: Exclude | None,
    response_by_alias: bool,
    response_exclude_unset: bool,
    response_exclude_defaults: bool,
    response_exclude_none: bool,
    response_custom_encoder: CustomEncoder | None,
    response_json_encoder: JSONEncoder,
) -> Response:
    return Response(
        status=int(status_code),
        content_type=response_content_type,
        charset=response_charset,
        zlib_executor=response_zlib_executor,
        zlib_executor_size=response_zlib_executor_size,
        include=response_include_fields,
        exclude=response_exclude_fields,
        by_alias=response_by_alias,
        exclude_unset=response_exclude_unset,
        exclude_defaults=response_exclude_defaults,
        exclude_none=response_exclude_none,
        custom_encoder=response_custom_encoder,
        json_encoder=response_json_encoder,
    )


def handler_validation_wrapper(
    handler: Handler,
    *,
    status_code: HTTPStatus,
    response_validate: bool,
    response_type: type[Any] | None,
    response_content_type: str | ContentType | None,
    response_charset: str | Charset,
    response_zlib_executor: Executor | None,
    response_zlib_executor_size: int | None,
    response_json_encoder: JSONEncoder,
    response_include_fields: Include | None,
    response_exclude_fields: Exclude | None,
    response_by_alias: bool,
    response_exclude_unset: bool,
    response_exclude_defaults: bool,
    response_exclude_none: bool,
    response_custom_encoder: CustomEncoder | None,
) -> Handler:
    """Bind extraction, validation, injections, and minimal response creation."""
    if not isinstance(handler, HandlerPartial):
        handler = _di_wrap(handler)

    handler_controller = controller_factory(
        handler,
        request_attr_can_declare_fst=True,
        status_code=status_code,
        response_validate=response_validate,
        response_type=response_type,
        response_content_type=response_content_type,
        response_charset=str(response_charset),
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

    @wraps(handler)
    async def inner(request: Request) -> StreamResponse:
        pre_response: Response | None = None
        validated_data = await handler_controller.validate_request(request)
        if handler_controller.request_attribute_name:
            validated_data[handler_controller.request_attribute_name] = request
        if handler_controller.response_attribute_name:
            pre_response = _create_pre_response(
                status_code=status_code,
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
            validated_data[handler_controller.response_attribute_name] = pre_response

        handler_result = await handler(**validated_data)
        return await handler_controller.create_response(handler_result, pre_response)

    return inner


def view_validation_wrapper(
    view: type[View],
    *,
    method: HTTPMethod,
    status_code: HTTPStatus,
    response_validate: bool,
    response_type: type[Any] | None,
    response_content_type: str | ContentType | None,
    response_charset: str | Charset,
    response_zlib_executor: Executor | None,
    response_zlib_executor_size: int | None,
    response_json_encoder: JSONEncoder,
    response_include_fields: Include | None,
    response_exclude_fields: Exclude | None,
    response_by_alias: bool,
    response_exclude_unset: bool,
    response_exclude_defaults: bool,
    response_exclude_none: bool,
    response_custom_encoder: CustomEncoder | None,
) -> type[View]:
    """Prepare class-handler methods for their future milestone-10 router."""
    handler_controllers = {}
    view_http_methods = {name.lower() for name in dir(view) if name.upper() in METH_ALL}

    if method == HTTPMethod.any and 'get' in view_http_methods and 'head' not in view_http_methods:
        setattr(view, HTTPMethod.head.value.lower(), getattr(view, HTTPMethod.get.value.lower()))
        view_http_methods.add('head')

    method_names = view_http_methods if method == HTTPMethod.any else {method.value.lower()}
    if method == HTTPMethod.head and 'head' not in view_http_methods:
        get_handler = getattr(view, HTTPMethod.get.value.lower(), None)
        if get_handler is None:
            raise AllowHeadError
        setattr(view, HTTPMethod.head.value.lower(), get_handler)

    for method_name in method_names:
        try:
            method_handler = cast('Handler', getattr(view, method_name))
        except AttributeError as exc:
            raise MethodNotFoundInViewError(method_name=method_name) from exc
        method_handler = _di_wrap(method_handler)
        setattr(view, method_name, method_handler)
        handler_controllers[method_name] = controller_factory(
            method_handler,
            status_code=status_code,
            response_validate=response_validate,
            response_type=response_type,
            response_content_type=response_content_type,
            response_charset=str(response_charset),
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

    @wraps(view)
    async def inner(request: Request) -> StreamResponse:
        method_name = request.method.lower()
        controller = handler_controllers.get(method_name)
        method_handler = getattr(view, method_name, None)
        if controller is None or method_handler is None:
            raise HTTPMethodNotAllowed(request.method, {name.upper() for name in handler_controllers})

        pre_response: Response | None = None
        validated_data = await controller.validate_request(request)
        if controller.request_attribute_name:
            validated_data[controller.request_attribute_name] = request
        if controller.response_attribute_name:
            pre_response = _create_pre_response(
                status_code=status_code,
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
            validated_data[controller.response_attribute_name] = pre_response

        instance = view(request)
        bound_handler = cast('Handler', getattr(instance, method_name))
        handler_result = await bound_handler(**validated_data)
        return await controller.create_response(handler_result, pre_response)

    # NOTE(08-middleware-mounts): middleware_validation_wrapper переносится в middlewares/runner.py
    return cast('type[View]', inner)
