from concurrent.futures import Executor
from functools import partial, wraps
from typing import Any, Optional, Type, TYPE_CHECKING, Union

from aiohttp.typedefs import JSONEncoder

from rapidy import hdrs
from rapidy._endpoint_handlers import endpoint_handler_builder
from rapidy._endpoint_helpers import create_response
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import Handler, HandlerType, MethodHandler, Middleware
from rapidy.web_middlewares import middleware as middleware_deco
from rapidy.web_response import Response, StreamResponse

if TYPE_CHECKING:
    from rapidy.web_request import Request
    from rapidy.web_urldispatcher import View


def handler_validation_wrapper(
        handler: Handler,
        *,
        response_validate: bool,
        response_type: Union[Type[Any], None],
        response_content_type: Union[str, ContentType],
        response_charset: Union[str, Charset],
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
) -> Handler:
    endpoint_handler = endpoint_handler_builder(
        handler,
        request_attr_can_declare=True,
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
    async def inner(request: 'Request') -> StreamResponse:
        pre_response: Optional[Response] = None

        validated_data = await endpoint_handler.validate_request(request)

        if endpoint_handler.request_attribute_name:
            validated_data[endpoint_handler.request_attribute_name] = request

        if endpoint_handler.response_attribute_name:
            pre_response = create_response(
                content_type=response_content_type,
                charset=response_charset,
                zlib_executor=response_zlib_executor,
                zlib_executor_size=response_zlib_executor_size,
            )
            validated_data[endpoint_handler.response_attribute_name] = pre_response

        handler_result = await handler(**validated_data)

        return endpoint_handler.validate_response(handler_result, pre_response)

    return inner


def view_validation_wrapper(
        view: Type['View'],
        *,
        response_validate: bool,
        response_type: Union[Type[Any], None],
        response_content_type: Union[str, ContentType],
        response_charset: Union[str, Charset],
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
) -> 'View':
    request_handlers = {}

    for method in (  # noqa: WPS335 WPS352
        handler_attr
        for handler_attr in dir(view)
        if handler_attr.upper() in hdrs.METH_ALL
    ):
        method_handler: MethodHandler = getattr(view, method)
        request_handlers[method.lower()] = endpoint_handler_builder(
            method_handler,
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
    async def inner(request: 'Request') -> StreamResponse:
        pre_response: Optional[Response] = None

        instance_view = view(request)
        method_name = request.method.lower()

        try:
            endpoint_handler = request_handlers[method_name]
        except KeyError:
            instance_view._raise_allowed_methods()
            raise  # for linters only

        try:
            method = getattr(instance_view, method_name)  # noqa: WPS442
        except AttributeError:
            instance_view._raise_allowed_methods()
            raise  # for linters only

        validated_data = await endpoint_handler.validate_request(request)

        if endpoint_handler.response_attribute_name:
            pre_response = create_response(
                content_type=response_content_type,
                charset=response_charset,
                zlib_executor=response_zlib_executor,
                zlib_executor_size=response_zlib_executor_size,
            )
            validated_data[endpoint_handler.response_attribute_name] = pre_response

        async def _inner_method(**kwargs: Any) -> StreamResponse:
            handler_result = await method(**kwargs)
            return endpoint_handler.validate_response(handler_result, pre_response)

        setattr(instance_view, method_name, partial(_inner_method, **validated_data))

        return await instance_view

    return inner


def middleware_validation_wrapper(
        middleware: Middleware,
        *,
        response_validate: bool,
        response_type: Union[Type[Any], None],
        response_content_type: Union[str, ContentType],
        response_charset: Union[str, Charset],
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
) -> Middleware:
    endpoint_handler = endpoint_handler_builder(
        middleware,
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
    async def inner(request: 'Request', handler: HandlerType) -> StreamResponse:
        pre_response: Optional[Response] = None

        validated_data = await endpoint_handler.validate_request(request=request)
        if endpoint_handler.response_attribute_name:
            pre_response = create_response(
                content_type=response_content_type,
                charset=response_charset,
                zlib_executor=response_zlib_executor,
                zlib_executor_size=response_zlib_executor_size,
            )
            validated_data[endpoint_handler.response_attribute_name] = pre_response

        handler_result = await middleware(request, handler, **validated_data)
        return endpoint_handler.validate_response(handler_result, pre_response)

    return inner
