from concurrent.futures import Executor
from typing import Any, Iterable, List, Optional, Type, Union

from aiohttp.abc import AbstractView
from aiohttp.web_routedef import RouteDef

from rapidy._base_exceptions import RapidyException
from rapidy.constants import CLIENT_MAX_SIZE, DEFAULT_JSON_ENCODER
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType, MethodName
from rapidy.lifespan import is_async_callable, LifespanCTX, LifespanHook
from rapidy.routing.http.base import BaseHTTPRouter
from rapidy.typedefs import HandlerOrView, HTTPRouterType, JSONEncoder, Middleware, Unset
from rapidy.web_app import Application

__all__ = (
    'HTTPRouterType',
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
    'options',
    'view',
)


class IncorrectTypeViewError(RapidyException):
    message = '`handler` must be a subclass of `AbstractView`. Current type: `{type_handler}`'


class IncorrectHandlerTypeError(RapidyException):
    message = '`handler` must be a subclass of `AbstractView` or async function`. Current type: `{type_handler}`'


def is_view(handler: Any) -> bool:
    return isinstance(handler, type) and issubclass(handler, AbstractView)


class HTTPRouteHandler(BaseHTTPRouter):
    _method_name: MethodName

    __slots__ = (
        '_method_name',
        '_route_def',
        '_real_handler',
        '_fn',
        'path',
    )

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        super().__init__(path=path)

        self._route_def = None
        self._real_handler = None

        def inner(handler: HandlerOrView) -> 'HTTPRouteHandler':
            self._real_handler = handler

            self._route_def = RouteDef(
                self._method_name.value,
                path,
                handler,
                kwargs={
                    'name': name,
                    'response_validate': response_validate,
                    'response_type': response_type,
                    'response_content_type': response_content_type,
                    'response_charset': response_charset,
                    'response_zlib_executor': response_zlib_executor,
                    'response_zlib_executor_size': response_zlib_executor_size,
                    'response_include_fields': response_include_fields,
                    'response_exclude_fields': response_exclude_fields,
                    'response_by_alias': response_by_alias,
                    'response_exclude_unset': response_exclude_unset,
                    'response_exclude_defaults': response_exclude_defaults,
                    'response_exclude_none': response_exclude_none,
                    'response_custom_encoder': response_custom_encoder,
                    'response_json_encoder': response_json_encoder,
                    **kwargs,
                },
            )
            return self

        self._fn = inner

    def __call__(self, handler: HandlerOrView) -> 'HTTPRouteHandler':
        return self._fn(handler)

    @classmethod
    def handler(
        cls,
        path: str,
        handler: HandlerOrView,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> 'HTTPRouteHandler':
        init = cls(
            path=path,
            name=name,
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
        return init(handler)

    def register(self, application: Application) -> None:
        assert self._route_def  # noqa: S101

        handler = self._route_def.handler
        if not is_async_callable(handler):
            if not is_view(handler):
                raise IncorrectHandlerTypeError(type_handler=str(type(handler)))

            for handler_attr in dir(handler):
                if not handler_attr.startswith('_'):
                    h_method = getattr(handler, handler_attr)
                    if isinstance(h_method, HTTPRouteHandler):
                        h_method.register(application)

                        assert h_method._real_handler  # noqa: S101 SLF001

                        # register true handler (remove deco)
                        setattr(handler, handler_attr, h_method._real_handler)  # noqa: SLF001

        self._route_def.register(application.router)


class HTTPRouter(BaseHTTPRouter):
    __slots__ = (
        'path',
        'application',
    )

    def __init__(
        self,
        path: str,
        route_handlers: Iterable[HTTPRouterType] = (),
        *,
        middlewares: Optional[Iterable[Middleware]] = None,
        client_max_size: int = CLIENT_MAX_SIZE,
        lifespan: Optional[List[LifespanCTX]] = None,
        on_startup: Optional[List[LifespanHook]] = None,
        on_shutdown: Optional[List[LifespanHook]] = None,
        on_cleanup: Optional[List[LifespanHook]] = None,
    ) -> None:
        """Create an `rapidy` HTTPRouter instance.

        Args:
            path:
                HTTPRouter base path.
            route_handlers:
                A iterable of `rapidy.routing.http.base.BaseHTTPRouter`.
                All passed handlers will be registered in the application.
                >>> from rapidy import web
                >>> from rapidy.http import get, HTTPRouterType
                >>>
                >>> @get('/app_path1')
                >>> async def app_handler1() -> None: pass
                >>>
                >>> async def app_handler2() -> None: pass
                >>>
                >>> @get('/router_path1')
                >>> async def router_handler1() -> None: pass
                >>>
                >>> async def router_handler2() -> None: pass
                >>>
                >>> api_router = HTTPRouterType(
                >>>     '/api',
                >>>     route_handlers=[
                >>>         router_handler1,
                >>>         get.handler('/router_path2', router_handler2),
                >>>     ],
                >>> )
                >>>
                >>> app = web.Application(
                >>>     http_route_handlers=[
                >>>         api_router,  # add router
                >>>         app_handler1,
                >>>         get.handler('/app_path2', app_handler2),
                >>>     ]
                >>> )
            middlewares:
                List of middleware factories.
            client_max_size:
                Client`s maximum size in a request, in bytes.
                If a POST request exceeds this value, it raises an HTTPRequestEntityTooLarge exception.
            lifespan:
                A list of callables returning async context managers,
                wrapping the lifespan of the application.
                >>> @asynccontextmanager
                >>> async def lifespan_ctx(app: web.Application) -> AsyncGenerator[None, None]:
                >>>     try:
                >>>         await startup_func()
                >>>             yield
                >>>     finally:
                >>>         await shutdown_func()

                You can set this in two ways:
                >>> app = web.Application(lifespan=[lifespan_ctx, ...], ...)
                or
                >>> app.lifespan.append(lifespan_ctx)
            on_startup:
                A sequence of `rapidy.typedefs.LifespanHook` called during application startup.
                Developers may use this to run background tasks in the event loop
                along with the application`s request handler just after the application start-up.
                >>> def on_startup(app):
                >>>     pass

                >>> def on_startup():
                >>>     pass

                >>> async def on_startup(app):
                >>>     pass

                >>> async def on_startup():
                >>>     pass

                You can set this in two ways:
                >>> app = web.Application(on_startup=[on_startup, ...], ...)
                or
                >>> app.lifespan.on_startup.append(on_startup)
            on_shutdown:
                A sequence of `rapidy.types.LifespanHook` called during application shutdown.
                Developers may use this for gracefully closing long running connections,
                e.g. websockets and data streaming.
                >>> def on_shutdown(app):
                >>>     pass

                >>> def on_shutdown():
                >>>     pass

                >>> async def on_shutdown(app):
                >>>     pass

                >>> async def on_shutdown():
                >>>     pass
                You can set this in two ways:
                >>> app = web.Application(on_shutdown=[on_shutdown, ...], ...)
                or
                >>> app.lifespan.on_shutdown.append(on_shutdown)
            on_cleanup:
                A sequence of `rapidy.types.LifespanHook` called during application cleanup.
                Developers may use this for gracefully closing connections to database server etc.
                Signal handlers should have the following signature:
                >>> def on_cleanup(app):
                >>>     pass

                >>> def on_cleanup():
                >>>     pass

                >>> async def on_cleanup(app):
                >>>     pass

                >>> async def on_cleanup():
                >>>     pass

                >>> app = web.Application(on_cleanup=[on_cleanup, ...], ...)
        """
        super().__init__(path=path)

        self.application = Application(
            middlewares=middlewares,
            http_route_handlers=route_handlers,
            client_max_size=client_max_size,
            lifespan=lifespan,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            on_cleanup=on_cleanup,
        )

    def register(self, application: Application) -> None:
        application.add_subapp(prefix=self.path, subapp=self.application)


class get(HTTPRouteHandler):
    _method_name = MethodName.get

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        allow_head: bool = True,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for registering GET web-handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
            allow_head=allow_head,
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


class post(HTTPRouteHandler):
    _method_name = MethodName.post

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for registering POST web-handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
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


class put(HTTPRouteHandler):
    _method_name = MethodName.put

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for registering PUT web-handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
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


class patch(HTTPRouteHandler):
    _method_name = MethodName.patch

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for registering PATCH web-handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
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


class delete(HTTPRouteHandler):
    _method_name = MethodName.delete

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for registering DELETE web-handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
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


class view(HTTPRouteHandler):
    _method_name = MethodName.any

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for adding class-based view handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
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

    def __call__(self, handler: HandlerOrView) -> HTTPRouteHandler:
        """Wrap handler into a route handler."""
        if not is_view(handler):
            raise IncorrectTypeViewError(type_handler=str(type(handler)))
        return self._fn(handler)


class head(HTTPRouteHandler):
    _method_name = MethodName.head

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for registering HEAD web-handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
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


class options(HTTPRouteHandler):
    _method_name = MethodName.options

    def __init__(
        self,
        path: str,
        *,
        name: Optional[str] = None,
        response_validate: bool = True,
        response_type: Optional[Type[Any]] = Unset,
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
    ) -> None:
        """Create a new RouteDef item for registering OPTIONS web-handler.

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
            kwargs:
                Additional internal arguments.
        """
        super().__init__(
            path=path,
            name=name,
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
