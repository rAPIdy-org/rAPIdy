from concurrent.futures import Executor
from typing import Any, Callable, Optional, Type, Union

from aiohttp.abc import AbstractView
from aiohttp.helpers import sentinel
from aiohttp.typedefs import DEFAULT_JSON_ENCODER, JSONEncoder, PathLike
from aiohttp.web_routedef import AbstractRouteDef, RouteDef, RouteTableDef as AioHTTPRouteTableDef, StaticDef

from rapidy import hdrs
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.typedefs import HandlerType

__all__ = (
    'AbstractRouteDef',
    'RouteDef',
    'StaticDef',
    'RouteTableDef',
    'head',
    'options',
    'get',
    'post',
    'patch',
    'put',
    'delete',
    'route',
    'view',
    'static',
)

RouterDeco = Callable[[HandlerType], HandlerType]


def route(method: str, path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return RouteDef(method=method, path=path, handler=handler, kwargs=kwargs)


def head(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(method=hdrs.METH_HEAD, path=path, handler=handler, **kwargs)


def options(path: str, handler: HandlerType, **kwargs: Any) -> RouteDef:
    return route(method=hdrs.METH_OPTIONS, path=path, handler=handler, **kwargs)


def get(
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
) -> RouteDef:
    """Create a new RouteDef item for registering GET web-handler.

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
    return route(
        # aiohttp attrs
        method=hdrs.METH_GET,
        path=path,
        handler=handler,
        name=name,
        allow_head=allow_head,
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


def post(
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
) -> RouteDef:
    """Create a new RouteDef item for registering POST web-handler.

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
    return route(
        # aiohttp attrs
        method=hdrs.METH_POST,
        path=path,
        handler=handler,
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


def put(
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
) -> RouteDef:
    """Create a new RouteDef item for registering PUT web-handler.

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
    return route(
        # aiohttp attrs
        method=hdrs.METH_PUT,
        path=path,
        handler=handler,
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


def patch(
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
) -> RouteDef:
    """Create a new RouteDef item for registering PATCH web-handler.

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
    return route(
        # aiohttp attrs
        method=hdrs.METH_PATCH,
        path=path,
        handler=handler,
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


def delete(
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
) -> RouteDef:
    """Create a new RouteDef item for registering DELETE web-handler.

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
    return route(
        # aiohttp attrs
        method=hdrs.METH_DELETE,
        path=path,
        handler=handler,
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


def view(
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
) -> RouteDef:
    """Create a new RouteDef item for adding class-based view handler.

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
    return route(
        # aiohttp attrs
        method=hdrs.METH_ANY,
        path=path,
        handler=handler,
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


def static(prefix: str, path: PathLike, **kwargs: Any) -> StaticDef:
    return StaticDef(prefix, path, kwargs)


class RouteTableDef(AioHTTPRouteTableDef):
    def route(self, method: str, path: str, **kwargs: Any) -> RouterDeco:
        def inner(handler: HandlerType) -> HandlerType:
            self._items.append(RouteDef(method, path, handler, kwargs))
            return handler

        return inner

    def head(self, path: str, **kwargs: Any) -> RouterDeco:
        """Add a new RouteDef item for registering HEAD web-handler."""
        return self.route(hdrs.METH_HEAD, path, **kwargs)

    def get(
            self,
            path: str,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering GET web-handler.

        Args:
            path:
                Resource path spec.
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
        return self.route(
            # aiohttp attrs
            hdrs.METH_GET,
            path,
            name=name,
            allow_head=allow_head,
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

    def post(
            self,
            path: str,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering POST web-handler.

        Args:
            path:
                Resource path spec.
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
        return self.route(
            # aiohttp attrs
            hdrs.METH_POST,
            path,
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

    def put(
            self,
            path: str,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering PUT web-handler.

        Args:
            path:
                Resource path spec.
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
        return self.route(
            # aiohttp attrs
            hdrs.METH_PUT,
            path,
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

    def patch(
            self,
            path: str,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering PATCH web-handler.

        Args:
            path:
                Resource path spec.
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
        return self.route(
            # aiohttp attrs
            hdrs.METH_PATCH,
            path,
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

    def delete(
            self,
            path: str,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for registering DELETE web-handler.

        Args:
            path:
                Resource path spec.
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
        return self.route(
            # aiohttp attrs
            hdrs.METH_DELETE,
            path,
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

    def options(self, path: str, **kwargs: Any) -> RouterDeco:
        """Add a new RouteDef item for registering OPTIONS web-handler.

        Args:
            path:
                Resource path spec.
        """
        return self.route(hdrs.METH_OPTIONS, path, **kwargs)

    def view(
            self,
            path: str,
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
    ) -> RouterDeco:
        """Add a new RouteDef item for adding class-based view handler.

        Args:
            path:
                Resource path spec.
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
        return self.route(
            # aiohttp attrs
            hdrs.METH_ANY,
            path,
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
