from abc import ABC
from concurrent.futures import Executor
from types import FunctionType
from typing import Any, cast, Final, Optional, Type, Union

from aiohttp.abc import AbstractView
from aiohttp.helpers import sentinel
from aiohttp.typedefs import DEFAULT_JSON_ENCODER, JSONEncoder
from aiohttp.web_urldispatcher import (
    _ExpectHandler,
    _requote_path,
    AbstractResource,
    AbstractRoute,
    DynamicResource as AioHTTPDynamicResource,
    PlainResource as AioHTTPPlainResource,
    PrefixedSubAppResource,
    Resource as AioHTTPResource,
    ResourceRoute as AioHTTPResourceRoute,
    ROUTE_RE,
    StaticResource,
    UrlDispatcher as AioHTTPUrlDispatcher,
    UrlMappingMatchInfo,
    View,
)

from rapidy import hdrs
from rapidy._endpoint_validation_wrappers import handler_validation_wrapper, view_validation_wrapper
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import HandlerType

__all__ = [
    'UrlDispatcher',
    'UrlMappingMatchInfo',
    'AbstractResource',
    'Resource',
    'PlainResource',
    'PrefixedSubAppResource',
    'DynamicResource',
    'AbstractRoute',
    'ResourceRoute',
    'StaticResource',
    'View',
]

HEAD_METHOD_NAME: Final[str] = 'head'


class ResourceRoute(AioHTTPResourceRoute, ABC):
    def __init__(
            self,
            method: str,
            handler: HandlerType,
            resource: AbstractResource,
            *,
            expect_handler: Optional[_ExpectHandler] = None,
            **kwargs: Any,
    ) -> None:
        if method.lower() != HEAD_METHOD_NAME:
            if isinstance(handler, FunctionType):
                handler = handler_validation_wrapper(
                    handler,
                    response_validate=kwargs['response_validate'],
                    response_type=kwargs['response_type'],
                    response_content_type=kwargs['response_content_type'],
                    response_charset=kwargs['response_charset'],
                    response_zlib_executor=kwargs['response_zlib_executor'],
                    response_zlib_executor_size=kwargs['response_zlib_executor_size'],
                    response_include_fields=kwargs['response_include_fields'],
                    response_exclude_fields=kwargs['response_exclude_fields'],
                    response_by_alias=kwargs['response_by_alias'],
                    response_exclude_unset=kwargs['response_exclude_unset'],
                    response_exclude_defaults=kwargs['response_exclude_defaults'],
                    response_exclude_none=kwargs['response_exclude_none'],
                    response_custom_encoder=kwargs['response_custom_encoder'],
                    response_json_encoder=kwargs['response_json_encoder'],
                )
            elif issubclass(handler, View):  # type: ignore[arg-type]
                handler = view_validation_wrapper(
                    handler,  # type: ignore[arg-type]
                    response_validate=kwargs['response_validate'],
                    response_type=kwargs['response_type'],
                    response_content_type=kwargs['response_content_type'],
                    response_charset=kwargs['response_charset'],
                    response_zlib_executor=kwargs['response_zlib_executor'],
                    response_zlib_executor_size=kwargs['response_zlib_executor_size'],
                    response_include_fields=kwargs['response_include_fields'],
                    response_exclude_fields=kwargs['response_exclude_fields'],
                    response_by_alias=kwargs['response_by_alias'],
                    response_exclude_unset=kwargs['response_exclude_unset'],
                    response_exclude_defaults=kwargs['response_exclude_defaults'],
                    response_exclude_none=kwargs['response_exclude_none'],
                    response_custom_encoder=kwargs['response_custom_encoder'],
                    response_json_encoder=kwargs['response_json_encoder'],
                )

        super().__init__(method=method, handler=handler, expect_handler=expect_handler, resource=resource)


class Resource(AioHTTPResource, ABC):
    def add_route(
            self,
            method: str,
            handler: HandlerType,
            *,
            expect_handler: Optional[_ExpectHandler] = None,
            **kwargs: Any,
    ) -> 'ResourceRoute':
        for route_obj in self._routes:
            if route_obj.method == method or route_obj.method == hdrs.METH_ANY:  # noqa: WPS514
                raise RuntimeError(  # aiohttp code  # pragma: no cover
                    'Added route will never be executed, '
                    'method {route.method} is already '
                    'registered'.format(route=route_obj),
                )

        route_obj = ResourceRoute(method, handler, self, expect_handler=expect_handler, **kwargs)  # noqa: WPS440
        self.register_route(route_obj)  # noqa: WPS441

        return route_obj  # noqa: WPS441


class PlainResource(Resource, AioHTTPPlainResource):
    pass


class DynamicResource(Resource, AioHTTPDynamicResource):
    pass


class UrlDispatcher(AioHTTPUrlDispatcher):
    def add_resource(self, path: str, *, name: Optional[str] = None) -> Resource:
        if path and not path.startswith('/'):  # aiohttp code  # pragma: no cover
            raise ValueError('path should be started with / or be empty')

        # Reuse last added resource if path and name are the same
        if self._resources:
            resource = self._resources[-1]
            if resource.name == name and resource.raw_match(path):
                return cast(Resource, resource)

        if not ('{' in path or '}' in path or ROUTE_RE.search(path)):
            resource = PlainResource(_requote_path(path), name=name)
            self.register_resource(resource)
            return resource

        resource = DynamicResource(path, name=name)
        self.register_resource(resource)

        return resource

    def add_route(
            self,
            method: str,
            path: str,
            handler: HandlerType,
            *,
            name: Optional[str] = None,
            expect_handler: Optional[_ExpectHandler] = None,
            **kwargs: Any,
    ) -> AbstractRoute:
        resource = self.add_resource(path, name=name)
        return resource.add_route(method, handler, expect_handler=expect_handler, **kwargs)

    def add_get(
            self,
            path: str,
            handler: HandlerType,
            *,
            name: Optional[str] = None,
            allow_head: bool = True,
            response_validate: bool = True,
            response_type: Optional[Type[Any]] = sentinel,
            response_content_type: Union[str, ContentType, None] = None,
            response_charset: Union[str, Charset] = Charset.utf8,
            response_zlib_executor: Optional[Executor] = None,
            response_zlib_executor_size: Optional[int] = None,
            response_include_fields: Optional[Include] = None,
            response_exclude_fields: Optional[Exclude] = None,
            response_by_alias: bool = True,
            response_exclude_unset: bool = False,
            response_exclude_defaults: bool = False,
            response_exclude_none: bool = False,
            response_custom_encoder: Optional[CustomEncoder] = None,
            response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
            **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        Args:
            path:
                Resource path spec.
            handler:
                Route handler.
            name:
                Optional resource name.
            allow_head:
                If allow_head is True (default) the route for method HEAD is added with the same handler as for GET.
                If name is provided the name for HEAD route is suffixed with '-head'.
                For example
                >>> @get(path, handler, name='route')
                >>> def handler(request): ...
                call adds two routes: first for GET with name 'route' and second for HEAD with name 'route-head'.
            response_validate:
                Flag determines whether the handler response should be validated.
            response_type:
                Handler response type.
                This attribute is used to create the response model.
                If this attribute is defined, it overrides the handler return annotation logic.
            response_content_type:
                Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
            response_charset:
                The `charset` that will be used to encode and decode handler result data.
            response_zlib_executor:
                Executor to use for zlib compression
            response_zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            response_include_fields:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            response_exclude_fields:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            response_by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            response_exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            response_exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            response_exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            response_custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            response_json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True
        """
        resource = self.add_resource(path, name=name)
        if allow_head:
            resource.add_route(hdrs.METH_HEAD, handler, **kwargs)
        return resource.add_route(
            hdrs.METH_GET,
            handler,
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
            **kwargs,
        )

    def add_post(
            self,
            path: str,
            handler: HandlerType,
            *,
            name: Optional[str] = None,
            response_validate: bool = True,
            response_type: Optional[Type[Any]] = sentinel,
            response_content_type: Union[str, ContentType, None] = None,
            response_charset: Union[str, Charset] = Charset.utf8,
            response_zlib_executor: Optional[Executor] = None,
            response_zlib_executor_size: Optional[int] = None,
            response_include_fields: Optional[Include] = None,
            response_exclude_fields: Optional[Exclude] = None,
            response_by_alias: bool = True,
            response_exclude_unset: bool = False,
            response_exclude_defaults: bool = False,
            response_exclude_none: bool = False,
            response_custom_encoder: Optional[CustomEncoder] = None,
            response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
            **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method POST.

        Args:
            path:
                Resource path spec.
            handler:
                Route handler.
            name:
                Optional resource name.
            response_validate:
                Flag determines whether the handler response should be validated.
            response_type:
                Handler response type.
                This attribute is used to create the response model.
                If this attribute is defined, it overrides the handler return annotation logic.
            response_content_type:
                Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
            response_charset:
                The `charset` that will be used to encode and decode handler result data.
            response_zlib_executor:
                Executor to use for zlib compression
            response_zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            response_include_fields:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            response_exclude_fields:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            response_by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            response_exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            response_exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            response_exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            response_custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            response_json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True
        """
        return self.add_route(
            # aiohttp attrs
            hdrs.METH_POST,
            path,
            handler,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def add_put(
            self,
            path: str,
            handler: HandlerType,
            *,
            name: Optional[str] = None,
            response_validate: bool = True,
            response_type: Optional[Type[Any]] = sentinel,
            response_content_type: Union[str, ContentType, None] = None,
            response_charset: Union[str, Charset] = Charset.utf8,
            response_zlib_executor: Optional[Executor] = None,
            response_zlib_executor_size: Optional[int] = None,
            response_include_fields: Optional[Include] = None,
            response_exclude_fields: Optional[Exclude] = None,
            response_by_alias: bool = True,
            response_exclude_unset: bool = False,
            response_exclude_defaults: bool = False,
            response_exclude_none: bool = False,
            response_custom_encoder: Optional[CustomEncoder] = None,
            response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
            **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method PUT.

        Args:
            path:
                Resource path spec.
            handler:
                Route handler.
            name:
                Optional resource name.
            response_validate:
                Flag determines whether the handler response should be validated.
            response_type:
                Handler response type.
                This attribute is used to create the response model.
                If this attribute is defined, it overrides the handler return annotation logic.
            response_content_type:
                Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
            response_charset:
                The `charset` that will be used to encode and decode handler result data.
            response_zlib_executor:
                Executor to use for zlib compression
            response_zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            response_include_fields:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            response_exclude_fields:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            response_by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            response_exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            response_exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            response_exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            response_custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            response_json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True
        """
        return self.add_route(
            # aiohttp attrs
            hdrs.METH_PUT,
            path,
            handler,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def add_patch(
            self,
            path: str,
            handler: HandlerType,
            *,
            name: Optional[str] = None,
            response_validate: bool = True,
            response_type: Optional[Type[Any]] = sentinel,
            response_content_type: Union[str, ContentType, None] = None,
            response_charset: Union[str, Charset] = Charset.utf8,
            response_zlib_executor: Optional[Executor] = None,
            response_zlib_executor_size: Optional[int] = None,
            response_include_fields: Optional[Include] = None,
            response_exclude_fields: Optional[Exclude] = None,
            response_by_alias: bool = True,
            response_exclude_unset: bool = False,
            response_exclude_defaults: bool = False,
            response_exclude_none: bool = False,
            response_custom_encoder: Optional[CustomEncoder] = None,
            response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
            **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method PATCH.

        Args:
            path:
                Resource path spec.
            handler:
                Route handler.
            name:
                Optional resource name.
            response_validate:
                Flag determines whether the handler response should be validated.
            response_type:
                Handler response type.
                This attribute is used to create the response model.
                If this attribute is defined, it overrides the handler return annotation logic.
            response_content_type:
                Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
            response_charset:
                The `charset` that will be used to encode and decode handler result data.
            response_zlib_executor:
                Executor to use for zlib compression
            response_zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            response_include_fields:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            response_exclude_fields:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            response_by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            response_exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            response_exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            response_exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            response_custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            response_json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True
        """
        return self.add_route(
            # aiohttp attrs
            hdrs.METH_PATCH,
            path,
            handler,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def add_delete(
            self,
            path: str,
            handler: HandlerType,
            *,
            name: Optional[str] = None,
            response_validate: bool = True,
            response_type: Optional[Type[Any]] = sentinel,
            response_content_type: Union[str, ContentType, None] = None,
            response_charset: Union[str, Charset] = Charset.utf8,
            response_zlib_executor: Optional[Executor] = None,
            response_zlib_executor_size: Optional[int] = None,
            response_include_fields: Optional[Include] = None,
            response_exclude_fields: Optional[Exclude] = None,
            response_by_alias: bool = True,
            response_exclude_unset: bool = False,
            response_exclude_defaults: bool = False,
            response_exclude_none: bool = False,
            response_custom_encoder: Optional[CustomEncoder] = None,
            response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
            **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method DELETE.

        Args:
            path:
                Resource path spec.
            handler:
                Route handler.
            name:
                Optional resource name.
            response_validate:
                Flag determines whether the handler response should be validated.
            response_type:
                Handler response type.
                This attribute is used to create the response model.
                If this attribute is defined, it overrides the handler return annotation logic.
            response_content_type:
                Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
            response_charset:
                The `charset` that will be used to encode and decode handler result data.
            response_zlib_executor:
                Executor to use for zlib compression
            response_zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            response_include_fields:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            response_exclude_fields:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            response_by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            response_exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            response_exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            response_exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            response_custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            response_json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True
        """
        return self.add_route(
            # aiohttp attrs
            hdrs.METH_DELETE,
            path,
            handler,
            name=name,
            **kwargs,
            # rapidy attrs
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

    def add_view(
            self,
            path: str,
            handler: Type[AbstractView],
            *,
            name: Optional[str] = None,
            response_validate: bool = True,
            response_type: Optional[Type[Any]] = sentinel,
            response_content_type: Union[str, ContentType, None] = None,
            response_charset: Union[str, Charset] = Charset.utf8,
            response_zlib_executor: Optional[Executor] = None,
            response_zlib_executor_size: Optional[int] = None,
            response_include_fields: Optional[Include] = None,
            response_exclude_fields: Optional[Exclude] = None,
            response_by_alias: bool = True,
            response_exclude_unset: bool = False,
            response_exclude_defaults: bool = False,
            response_exclude_none: bool = False,
            response_custom_encoder: Optional[CustomEncoder] = None,
            response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
            **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with ANY methods for a class-based view.

        Args:
            path:
                Resource path spec.
            handler:
                Route handler.
            name:
                Optional resource name.
            response_validate:
                Flag determines whether the handler response should be validated.
            response_type:
                Handler response type.
                This attribute is used to create the response model.
                If this attribute is defined, it overrides the handler return annotation logic.
            response_content_type:
                Attribute defines the `Content-Type` header and performs post-processing of the endpoint handler return.
            response_charset:
                The `charset` that will be used to encode and decode handler result data.
            response_zlib_executor:
                Executor to use for zlib compression
            response_zlib_executor_size:
                Length in bytes which will trigger zlib compression of body to happen in an executor
            response_include_fields:
                Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
            response_exclude_fields:
                Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
            response_by_alias:
                Pydantic's `by_alias` parameter, passed to Pydantic models to define
                if the output should use the alias names (when provided) or the Python
                attribute names. In an API, if you set an alias, it's probably because you
                want to use it in the result, so you probably want to leave this set to `True`.
            response_exclude_unset:
                Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that were not explicitly
                set (and that only had their default values).
            response_exclude_defaults:
                Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
                if it should exclude from the output the fields that had the same default
                value, even when they were explicitly set.
            response_exclude_none:
                Pydantic's `exclude_none` parameter, passed to Pydantic models to define
                if it should exclude from the output any fields that have a `None` value.
            response_custom_encoder:
                Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
            response_json_encoder:
                Any callable that accepts an object and returns a JSON string.
                Will be used if dumps=True
        """
        return self.add_route(
            # aiohttp attrs
            hdrs.METH_ANY,
            path,
            handler,
            name=name,
            **kwargs,
            # rapidy attrs
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
