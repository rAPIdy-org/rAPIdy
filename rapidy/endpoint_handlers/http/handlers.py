from __future__ import annotations

from concurrent.futures import Executor
from functools import partial, wraps
from http import HTTPStatus
from typing import Any, cast, Type, TYPE_CHECKING

from aiohttp.hdrs import METH_ALL

from rapidy._base_exceptions import RapidyHandlerException
from rapidy.depends import inject_http
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.endpoint_handlers.http.controller import controller_factory
from rapidy.enums import Charset, ContentType, MethodName
from rapidy.routing.http.helper_types import HandlerPartial
from rapidy.typedefs import CallNext, Handler, JSONEncoder, Middleware, UnsetType
from rapidy.web_middlewares import middleware as middleware_deco
from rapidy.web_response import Response, StreamResponse

if TYPE_CHECKING:
    from rapidy.web_request import Request
    from rapidy.web_urldispatcher import View


class AllowHeadError(RapidyHandlerException):
    """Exception raised when the `head` method cannot be automatically defined in `View`.

    This occurs when the `get` method is not defined, which is required for `head` to be derived.
    """

    message = (
        'Cannot automatically define the `head` method in `View` because the `get` method is not defined.'
        '\nThis is internal `rAPIdy` error, please open the issue - https://github.com/rAPIdy-org/rAPIdy/issues/new'
    )


class MethodNotFoundInViewError(RapidyHandlerException):
    """Exception raised when a method is not found in the `View` class.

    Attributes:
        message (str): The error message describing the issue.
    """

    message = 'Failed to register View - method named `{method_name}` was not found.'


class MethodAlreadyRegisteredError(ValueError):
    """Exception raised when a method is already registered."""


def handler_validation_wrapper(
    handler: Handler,
    *,
    # response
    status_code: HTTPStatus,
    response_validate: bool,
    response_type: Type[Any] | None,
    response_content_type: str | ContentType | None,
    response_charset: str | Charset,
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
) -> Handler:
    """Wraps the handler with validation and response preparation.

    Args:
        handler (Handler): The request handler to wrap.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Whether to validate the response.
        response_type (Optional[Type[Any]]): The expected response type.
        response_content_type (Union[str, ContentType, None]): The response content type.
        response_charset (Union[str, Charset]): The charset for the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): Size for zlib compression.
        response_json_encoder (JSONEncoder): JSON encoder for the response.
        response_include_fields (Optional[Include]): Fields to include in the response.
        response_exclude_fields (Optional[Exclude]): Fields to exclude from the response.
        response_by_alias (bool): Whether to use alias for the response.
        response_exclude_unset (bool): Whether to exclude unset fields.
        response_exclude_defaults (bool): Whether to exclude default values.
        response_exclude_none (bool): Whether to exclude fields with `None` values.
        response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.

    Returns:
        Handler: The wrapped handler function.
    """

    if not isinstance(handler, HandlerPartial):
        handler = inject_http(handler)

    handler_controller = controller_factory(
        handler,
        request_attr_can_declare_fst=True,
        status_code=status_code,
        response_validate=response_validate,
        response_type=response_type,
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

    @wraps(handler)
    async def inner(request: Request) -> StreamResponse:
        """Inner function to handle the request, validate, and create a response.

        Args:
            request (Request): The HTTP request object.

        Returns:
            StreamResponse: The response to be sent back.
        """
        pre_response: Response | None = None

        validated_data = await handler_controller.validate_request(request)

        if handler_controller.request_attribute_name:
            validated_data[handler_controller.request_attribute_name] = request

        if handler_controller.response_attribute_name:
            pre_response = Response(
                status=status_code,
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
            validated_data[handler_controller.response_attribute_name] = pre_response

        handler_result = await handler(**validated_data)

        return await handler_controller.create_response(handler_result, pre_response)

    return inner


def view_validation_wrapper(  # noqa: C901
    view: Type[View],
    *,
    method: MethodName,
    # response
    status_code: HTTPStatus,
    response_validate: bool,
    response_type: Type[Any] | None,
    response_content_type: str | ContentType | None,
    response_charset: str | Charset,
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
) -> Type[View]:
    """Wraps the view with validation for HTTP methods and response preparation.

    Args:
        view (Type['View']): The view class to wrap.
        method (MethodName): The HTTP method to validate.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Whether to validate the response.
        response_type (Optional[Type[Any]]): The expected response type.
        response_content_type (Union[str, ContentType, None]): The response content type.
        response_charset (Union[str, Charset]): The charset for the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): Size for zlib compression.
        response_json_encoder (JSONEncoder): JSON encoder for the response.
        response_include_fields (Optional[Include]): Fields to include in the response.
        response_exclude_fields (Optional[Exclude]): Fields to exclude from the response.
        response_by_alias (bool): Whether to use alias for the response.
        response_exclude_unset (bool): Whether to exclude unset fields.
        response_exclude_defaults (bool): Whether to exclude default values.
        response_exclude_none (bool): Whether to exclude fields with `None` values.
        response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.

    Returns:
        Type['View']: The wrapped view class.
    """
    handler_controllers = {}
    view_http_methods = {handler_attr for handler_attr in dir(view) if handler_attr.upper() in METH_ALL}
    # NOTE! `view` does not support parameter inheritance.

    if method != MethodName.any:
        method_name = method.value.lower()
        if method not in view_http_methods and method == MethodName.head:
            # aiohttp `View` does not support `allow_head` attr in `get`, but `rAPIdy` does.
            get_method = getattr(view, MethodName.get.lower())
            if not get_method:
                raise AllowHeadError

            setattr(view, method_name, get_method)

        try:
            method_handler: Handler = getattr(view, method_name)
        except AttributeError as method_not_found_error:
            raise MethodNotFoundInViewError(method_name=method_name) from method_not_found_error

        method_handler = inject_http(method_handler)

        setattr(view, method_name, method_handler)

        # FIXME(daniil.grois): duplicate code
        handler_controllers[method_name] = controller_factory(
            method_handler,
            status_code=status_code,
            response_validate=response_validate,
            response_type=response_type,
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

    else:
        for method_name in view_http_methods:
            # FIXME(daniil.grois):
            #  rapidy always re-creates a controller wrapper over each handler
            #  even if some methods have already been defined beforehand
            #  NOTE: only affects the creation of unnecessary objects
            #  >>> app = web.Application()
            #  >>> app.router.add_get('/test/{foo}', FooView)
            #  >>> app.router.add_view('/test', FooView)  # recreate all controllers

            # FIXME(daniil.grois): duplicate code
            try:
                method_handler: Handler = getattr(view, method_name)  # type: ignore[no-redef]
            except AttributeError as method_not_found_error:
                raise MethodNotFoundInViewError(method_name=method_name) from method_not_found_error

            method_handler = inject_http(method_handler)

            setattr(view, method_name, method_handler)

            handler_controllers[method_name] = controller_factory(
                method_handler,
                status_code=status_code,
                response_validate=response_validate,
                response_type=response_type,
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

    @wraps(view)
    async def inner(request: Request) -> StreamResponse:
        """Inner function to handle the request and create a response.

        Args:
            request (Request): The HTTP request object.

        Returns:
            StreamResponse: The response to be sent back.
        """
        pre_response: Response | None = None

        instance_view = view(request)
        method_name = request.method.lower()

        try:
            endpoint_handler = handler_controllers[method_name]
        except KeyError:
            instance_view._raise_allowed_methods()  # noqa: SLF001
            raise  # for linters only

        try:
            method = getattr(instance_view, method_name)
        except AttributeError:
            instance_view._raise_allowed_methods()  # noqa: SLF001
            raise  # for linters only

        validated_data = await endpoint_handler.validate_request(request)

        if endpoint_handler.request_attribute_name:
            validated_data[endpoint_handler.request_attribute_name] = request

        if endpoint_handler.response_attribute_name:
            pre_response = Response(
                status=status_code,
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
            validated_data[endpoint_handler.response_attribute_name] = pre_response

        async def _inner_method(**kwargs: Any) -> StreamResponse:
            handler_result = await method(**kwargs)
            return await endpoint_handler.create_response(handler_result, pre_response)

        setattr(instance_view, method_name, partial(_inner_method, **validated_data))

        return await instance_view

    return cast(Type['View'], inner)


def middleware_validation_wrapper(
    middleware: Middleware,
    *,
    # response
    status_code: int | HTTPStatus,
    response_validate: bool,
    response_type: Type[Any] | None | UnsetType,
    response_content_type: str | ContentType | None,
    response_charset: str | Charset,
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
) -> Middleware:
    """Wraps a middleware with validation and response preparation.

    Args:
        middleware (Middleware): The middleware to wrap.
        status_code (int): The default status code to be used for the response.
        response_validate (bool): Whether to validate the response.
        response_type (Union[Type[Any], None, UnsetType]): The expected response type.
        response_content_type (Union[str, ContentType, None]): The response content type.
        response_charset (Union[str, Charset]): The charset for the response.
        response_zlib_executor (Optional[Executor]): Executor for zlib compression.
        response_zlib_executor_size (Optional[int]): Size for zlib compression.
        response_json_encoder (JSONEncoder): JSON encoder for the response.
        response_include_fields (Optional[Include]): Fields to include in the response.
        response_exclude_fields (Optional[Exclude]): Fields to exclude from the response.
        response_by_alias (bool): Whether to use alias for the response.
        response_exclude_unset (bool): Whether to exclude unset fields.
        response_exclude_defaults (bool): Whether to exclude default values.
        response_exclude_none (bool): Whether to exclude fields with `None` values.
        response_custom_encoder (Optional[CustomEncoder]): Custom encoder for the response.

    Returns:
        Middleware: The wrapped middleware function.
    """
    middleware = inject_http(middleware)

    handler_controller = controller_factory(
        middleware,
        status_code=status_code,
        response_validate=response_validate,
        response_type=response_type,
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

    @middleware_deco
    async def inner(request: Request, call_next: CallNext) -> StreamResponse:
        pre_response: Response | None = None

        validated_data = await handler_controller.validate_request(request=request)
        if handler_controller.response_attribute_name:
            pre_response = Response(
                status=status_code,
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
            validated_data[handler_controller.response_attribute_name] = pre_response

        handler_result = await middleware(request, call_next, **validated_data)

        return await handler_controller.create_response(handler_result, pre_response)

    return inner
