from functools import partial, wraps
from typing import Type, TYPE_CHECKING

from rapidy import hdrs
from rapidy._request_handlers import http_request_handler_builder
from rapidy.typedefs import Handler, HandlerType, MethodHandler, Middleware
from rapidy.web_middlewares import middleware as middleware_deco
from rapidy.web_response import StreamResponse

if TYPE_CHECKING:
    from rapidy.web_request import Request
    from rapidy.web_urldispatcher import View


def handler_validation_wrapper(handler: Handler) -> Handler:
    request_handler = http_request_handler_builder(handler, request_attr_can_declare=True)

    @wraps(handler)
    async def inner(request: 'Request') -> StreamResponse:
        validated_data = await request_handler.validate_request(request)

        if request_handler.request_attribute_name:
            validated_data[request_handler.request_attribute_name] = request

        return await handler(**validated_data)

    return inner


def view_validation_wrapper(view: Type['View']) -> 'View':
    request_handlers = {}

    for method in (  # noqa: WPS335 WPS352
        handler_attr
        for handler_attr in dir(view)
        if handler_attr.upper() in hdrs.METH_ALL
    ):
        method_handler: MethodHandler = getattr(view, method)
        request_handlers[method.lower()] = http_request_handler_builder(method_handler)

    @wraps(view)
    async def inner(request: 'Request') -> StreamResponse:
        instance_view = view(request)
        method_name = request.method.lower()

        try:
            request_handler = request_handlers[method_name]
        except KeyError:
            instance_view._raise_allowed_methods()
            raise  # for linters only

        try:
            method = getattr(instance_view, method_name)  # noqa: WPS442
        except AttributeError:
            instance_view._raise_allowed_methods()
            raise  # for linters only

        validated_data = await request_handler.validate_request(request)

        setattr(instance_view, method_name, partial(method, **validated_data))

        return await instance_view

    return inner


def middleware_validation_wrapper(middleware: Middleware) -> Middleware:
    request_handler = http_request_handler_builder(middleware)

    @middleware_deco
    async def inner(request: 'Request', handler: HandlerType) -> StreamResponse:
        validated_data = await request_handler.validate_request(request=request)
        return await middleware(request, handler, **validated_data)

    return inner
