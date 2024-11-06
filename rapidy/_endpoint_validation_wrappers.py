from concurrent.futures import Executor
from functools import partial, wraps
from typing import Any, Optional, Type, TYPE_CHECKING, Union, Iterable

from aiohttp.typedefs import JSONEncoder

from rapidy import hdrs
from rapidy._endpoint_handlers import http_endpoint_handler_builder, ws_endpoint_handler_builder
# from rapidy._endpoint_handlers import http_endpoint_handler_builder, ws_endpoint_handler_builder
from rapidy._endpoint_helpers import create_response, create_ws_response
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import CallNext, Handler, Middleware
from rapidy.web_middlewares import middleware as middleware_deco
from rapidy.web_response import Response, StreamResponse

if TYPE_CHECKING:
    from rapidy.web_request import Request
    from rapidy.web_urldispatcher import View


def handler_validation_wrapper(
        handler: Handler,
        *,
        response_validate: bool,
        response_type: Optional[Type[Any]],
        response_content_type: Union[str, ContentType, None],
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
    endpoint_handler = http_endpoint_handler_builder(
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

        handler_result = await handler(**validated_data)

        return endpoint_handler.validate_response(handler_result, pre_response)

    return inner


def ws_handler_validation_wrapper(
        handler: Handler,
        *,
        # ws
        ws_timeout: float,
        ws_receive_timeout: Optional[float],
        ws_autoclose: bool,
        ws_autoping: bool,
        ws_heartbeat: Optional[float],
        ws_protocols: Iterable[str],
        ws_compress: bool,
        ws_max_msg_size: int,
        # response
        response_validate: bool,
        response_type: Optional[Type[Any]],
        response_charset: Union[str, Charset],
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
    endpoint_handler = ws_endpoint_handler_builder(
        handler,
        request_attr_can_declare=True,
        # ws
        ws_timeout=ws_timeout,
        ws_receive_timeout=ws_receive_timeout,
        ws_autoclose=ws_autoclose,
        ws_autoping=ws_autoping,
        ws_heartbeat=ws_heartbeat,
        ws_protocols=ws_protocols,
        ws_compress=ws_compress,
        ws_max_msg_size=ws_max_msg_size,
        # msg
        msg_response_type=response_type,
        msg_response_validate=response_validate,
        msg_response_charset=response_charset,
        # response json preparer
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
        validated_data = await endpoint_handler.validate_request(request)
        return await endpoint_handler.validate_response(request=request, handler=handler, handler_data=validated_data)

        # # TODO ####
        # ws_message_attribute_name: Optional[str] = 'message'  # WSMessage
        #
        # # END ####
        # handler_data = {}
        #
        # ws_response = create_ws_response(
        #     timeout=ws_timeout,
        #     receive_timeout=ws_receive_timeout,
        #     autoclose=ws_autoclose,
        #     autoping=ws_autoping,
        #     heartbeat=ws_heartbeat,
        #     protocols=ws_protocols,
        #     compress=ws_compress,
        #     max_msg_size=ws_max_msg_size,
        # )
        #
        # if endpoint_handler.request_attribute_name:
        #     handler_data[endpoint_handler.request_attribute_name] = request
        #
        # if endpoint_handler.response_attribute_name:
        #     handler_data[endpoint_handler.response_attribute_name] = ws_response
        #
        # await ws_response.prepare(request=request)
        #
        # async for msg in ws_response:
        #     if ws_message_attribute_name:
        #         handler_data[ws_message_attribute_name] = msg
        #
        #     validate_data = {}
        #
        #     try:
        #         handler_result = await handler(**handler_data, **validate_data)
        #     finally:
        #         await ws_response.close()
        #
        #     return endpoint_handler.process_response(handler_result, pre_response)


        # validated_data = await endpoint_handler.validate_request(request)
        #
        # if endpoint_handler.request_attribute_name:
        #     validated_data[endpoint_handler.request_attribute_name] = request
        #
        # if endpoint_handler.response_attribute_name:
        #     pre_response = create_response(
        #         content_type=response_content_type,
        #         charset=response_charset,
        #         zlib_executor=response_zlib_executor,
        #         zlib_executor_size=response_zlib_executor_size,
        #         include=response_include_fields,
        #         exclude=response_exclude_fields,
        #         by_alias=response_by_alias,
        #         exclude_unset=response_exclude_unset,
        #         exclude_defaults=response_exclude_defaults,
        #         exclude_none=response_exclude_none,
        #         custom_encoder=response_custom_encoder,
        #         json_encoder=response_json_encoder,
        #     )
        #     validated_data[endpoint_handler.response_attribute_name] = pre_response
        #
        # handler_result = await handler(**validated_data)

        # return endpoint_handler.validate_response(handler_result, pre_response)

    return inner


def view_validation_wrapper(
        view: Type['View'],
        *,
        response_validate: bool,
        response_type: Optional[Type[Any]],
        response_content_type: Union[str, ContentType, None],
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
        method_handler: Handler = getattr(view, method)
        request_handlers[method.lower()] = http_endpoint_handler_builder(
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
            return endpoint_handler.validate_response(handler_result, pre_response)

        setattr(instance_view, method_name, partial(_inner_method, **validated_data))

        return await instance_view

    return inner


def middleware_validation_wrapper(
        middleware: Middleware,
        *,
        response_validate: bool,
        response_type: Optional[Type[Any]],
        response_content_type: Union[str, ContentType, None],
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
    endpoint_handler = http_endpoint_handler_builder(
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
    async def inner(request: 'Request', call_next: CallNext) -> StreamResponse:
        pre_response: Optional[Response] = None

        validated_data = await endpoint_handler.validate_request(request=request)
        if endpoint_handler.response_attribute_name:
            pre_response = create_response(
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

        handler_result = await middleware(request, call_next, **validated_data)
        return endpoint_handler.validate_response(handler_result, pre_response)

    return inner
