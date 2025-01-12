from abc import ABC
from concurrent.futures import Executor
from functools import partial
from typing import Any, Iterable, List, Optional, Type, Union

from aiohttp.web_routedef import RouteDef

from rapidy._base_exceptions import RapidyException, RapidyHandlerException
from rapidy.constants import CLIENT_MAX_SIZE, DEFAULT_JSON_ENCODER
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType, MethodName
from rapidy.lifespan import is_async_callable, LifespanCTX, LifespanHook
from rapidy.routing.http.base import BaseHTTPRouter
from rapidy.routing.http.helper_types import HandlerPartial
from rapidy.typedefs import ControllerHTTPRouterType, Handler, JSONEncoder, Middleware, Unset, UnsetType
from rapidy.web_app import Application

__all__ = (
    'HTTPRouter',
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
    'options',
    'controller',
)


def is_dunder_name(name: str) -> bool:
    return len(name) > 4 and name[:2] == name[-2:] == '__' and name[2] != '_' and name[-3] != '_'  # noqa: PLR2004


class MissingPathError(RapidyHandlerException):
    message = 'Handler must contain `path` attribute.'


class HandlerIsNotAsyncFuncTypeError(RapidyException):
    message = 'Handler must be an async function. Current type: `{type_handler}`'


def is_controller(handler: Any) -> bool:
    return isinstance(handler, controller)


class HTTPRouteHandler(BaseHTTPRouter, ABC):
    _method_name: MethodName

    _set_route_kwargs: dict[str, Any]
    _route_kwargs: dict[str, Any]

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Method is required to detect overridden values."""
        raw_kwargs = {
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
        }
        self._set_route_kwargs = {key: value for key, value in raw_kwargs.items() if value is not Unset}
        self.init(path=path, **self._set_route_kwargs)

    def init(
        self,
        path: Optional[str] = None,
        *,
        response_validate: bool = True,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
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
        """True __init__ method.

        Method is necessary for convenient management of default values.
        """
        self._route_kwargs = {
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
        }

        super().__init__(path=path)
        self._pre_route_def = partial(RouteDef, method=self._method_name.value)

    def __call__(self, handler: Any) -> 'HTTPRouteHandler':
        self._handler = handler
        return self

    @classmethod
    def reg(
        cls,
        path: str,
        handler: Union[Handler, ControllerHTTPRouterType],
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> 'HTTPRouteHandler':
        init = cls(
            path=path,
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

    def route_register(self, application: Application) -> None:
        if self.path is None:
            raise MissingPathError.create(handler=self._handler)

        route_def = self._pre_route_def(
            handler=self._handler,
            path=self.path,
            kwargs=self._route_kwargs,
        )
        if is_controller(self):
            for handler_attr_name in dir(self._handler):
                if is_dunder_name(handler_attr_name):
                    continue

                handler_attr = getattr(self._handler, handler_attr_name)
                if isinstance(handler_attr, HTTPRouteHandler):
                    handler_attr._handler = HandlerPartial(  # noqa: SLF001
                        controller_instance=self._handler,
                        handler=handler_attr._handler,  # noqa: SLF001
                    )
                    handler_attr.path = self._create_sub_route_path(sub_path=handler_attr.path)
                    handler_attr._route_kwargs = self._extend_kw(  # noqa: SLF001
                        sub_route_kwargs=handler_attr._route_kwargs,  # noqa: SLF001
                        sub_route_set_kwargs=handler_attr._set_route_kwargs,  # noqa: SLF001
                    )

                    handler_attr.route_register(application)
            return

        route_def.register(application.router)

    def _create_sub_route_path(self, sub_path: Optional[str]) -> str:
        if sub_path is None:
            assert self.path  # only for `mypy`  # noqa: S101
            return self.path

        return f'{self.path}{sub_path}'

    def _extend_kw(
        self,
        sub_route_kwargs: dict[str, Any],
        sub_route_set_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            **sub_route_kwargs,
            **self._set_route_kwargs,
            **sub_route_set_kwargs,
        }


class HTTPRouter(BaseHTTPRouter):
    __slots__ = (
        'path',
        'application',
    )

    def __init__(
        self,
        path: str,
        route_handlers: Iterable[BaseHTTPRouter] = (),
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
                >>>         get.reg('/router_path2', router_handler2),
                >>>     ],
                >>> )
                >>>
                >>> app = web.Application(
                >>>     http_route_handlers=[
                >>>         api_router,  # add router
                >>>         app_handler1,
                >>>         get.reg('/app_path2', app_handler2),
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

    def route_register(self, application: Application) -> None:
        application.add_subapp(prefix=self.path, subapp=self.application)


class HTTPMethodRouteHandler(HTTPRouteHandler):
    def __call__(self, handler: Handler) -> HTTPRouteHandler:
        """Wrap handler into a route handler."""
        if is_async_callable(handler):
            return super().__call__(handler)
        raise HandlerIsNotAsyncFuncTypeError(type_handler=str(type(handler)))


class controller(HTTPRouteHandler):
    _method_name = MethodName.any

    def __init__(
        self,
        path: str,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for adding class-based view handler.

        Args:
            path:
                Resource path spec.
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


class get(HTTPMethodRouteHandler):
    _method_name = MethodName.get

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        allow_head: bool = True,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for registering GET web-handler.

        Args:
            path:
                Resource path spec.
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


class post(HTTPMethodRouteHandler):
    _method_name = MethodName.post

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for registering POST web-handler.

        Args:
            path:
                Resource path spec.
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


class put(HTTPMethodRouteHandler):
    _method_name = MethodName.put

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for registering PUT web-handler.

        Args:
            path:
                Resource path spec.
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


class patch(HTTPMethodRouteHandler):
    _method_name = MethodName.patch

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for registering PATCH web-handler.

        Args:
            path:
                Resource path spec.
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


class delete(HTTPMethodRouteHandler):
    _method_name = MethodName.delete

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for registering DELETE web-handler.

        Args:
            path:
                Resource path spec.
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


class head(HTTPMethodRouteHandler):
    _method_name = MethodName.head

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for registering HEAD web-handler.

        Args:
            path:
                Resource path spec.
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


class options(HTTPMethodRouteHandler):
    _method_name = MethodName.options

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        response_validate: Union[bool, UnsetType] = Unset,
        response_type: Union[Type[Any], None, UnsetType] = Unset,
        response_content_type: Union[str, ContentType, None, UnsetType] = Unset,
        response_charset: Union[str, Charset, UnsetType] = Unset,
        response_zlib_executor: Union[Executor, None, UnsetType] = Unset,
        response_zlib_executor_size: Union[int, None, UnsetType] = Unset,
        response_include_fields: Union[Include, None, UnsetType] = Unset,
        response_exclude_fields: Union[Exclude, None, UnsetType] = Unset,
        response_by_alias: Union[bool, UnsetType] = Unset,
        response_exclude_unset: Union[bool, UnsetType] = Unset,
        response_exclude_defaults: Union[bool, UnsetType] = Unset,
        response_exclude_none: Union[bool, UnsetType] = Unset,
        response_custom_encoder: Union[CustomEncoder, None, UnsetType] = Unset,
        response_json_encoder: Union[JSONEncoder, UnsetType] = Unset,
        **kwargs: Any,
    ) -> None:
        """Create a new RouteDef item for registering OPTIONS web-handler.

        Args:
            path:
                Resource path spec.
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
