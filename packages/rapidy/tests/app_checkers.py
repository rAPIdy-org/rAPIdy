from concurrent.futures import Executor
from http import HTTPStatus
from typing import Any, Awaitable, Callable, Tuple, Type
from typing_extensions import TypeAlias

from aiohttp.pytest_plugin import AiohttpClient

from rapidy import Rapidy, web
from rapidy.constants import DEFAULT_JSON_ENCODER
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import Charset, ContentType
from rapidy.http import controller
from rapidy.typedefs import JSONEncoder, Unset, UnsetType
from rapidy.web_routedef import RouteTableDef
from tests.constants import ClientBodyExtractMethod, DEFAULT_RETURN_TYPE, DEFAULT_RETURN_VALUE

__all__ = (
    'AppFabric',
    'check_handlers',
    'check_handlers_all_response_models',
)


AppFabric: TypeAlias = Callable[..., Tuple[web.Application, ...]]

WEB_METHOD_NAMES: Tuple[str, ...] = ('get', 'post', 'put', 'patch', 'delete', 'options')  # aiohttp head -> no return


def _get_bound_method_by_http_method_name(obj: Any, method_name: str) -> Any:
    return getattr(obj, method_name)


# factories
def route_table_def(
    path: str,
    handler: Any,
    web_method: str,
    **handler_kwargs: Any,
) -> web.Application:
    routes = RouteTableDef()
    method = _get_bound_method_by_http_method_name(routes, web_method)
    method(path, **handler_kwargs)(handler)

    app = web.Application()
    app.add_routes(routes)
    return app


def simple_method_func(
    path: str,
    handler: Any,
    web_method: str,
    **handler_kwargs: Any,
) -> web.Application:
    method = _get_bound_method_by_http_method_name(web, web_method)

    app = web.Application()
    app.add_routes([method(path, handler, **handler_kwargs)])
    return app


def app_router_add_method(
    path: str,
    handler: Any,
    web_method: str,
    **handler_kwargs: Any,
) -> web.Application:
    app = web.Application()
    method = _get_bound_method_by_http_method_name(app.router, 'add_' + web_method)
    method(path, handler, **handler_kwargs)
    return app


def rapidy_router_method(
    path: str,
    handler: Any,
    web_method: str,
    **handler_kwargs: Any,
) -> web.Application:
    from rapidy.routing.http import routers

    method = _get_bound_method_by_http_method_name(routers, web_method)
    route = method(path, **handler_kwargs)(handler)
    return web.Application(http_route_handlers=[route])


def rapidy_router_method_reg(
    path: str,
    handler: Any,
    web_method: str,
    **handler_kwargs: Any,
) -> web.Application:
    from rapidy.routing.http import routers

    method = _get_bound_method_by_http_method_name(routers, web_method)
    return web.Application(http_route_handlers=[method.reg(path, handler, **handler_kwargs)])


view_supported_app_def = (
    route_table_def,
    simple_method_func,
    app_router_add_method,
)

all_app_def = (
    *view_supported_app_def,
    rapidy_router_method,
    rapidy_router_method_reg,
)


def create_view_supported_apps(
    path: str,
    handler: Any,
    web_method: str,
    **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    return tuple(app_def(path, handler, web_method, **handler_kwargs) for app_def in view_supported_app_def)


def create_all_apps(
    path: str,
    handler: Any,
    web_method: str,
    **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    return tuple(app_def(path, handler, web_method, **handler_kwargs) for app_def in all_app_def)


def create_all_function_handler_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    async def handler() -> handler_return_type:
        return return_value

    return create_all_apps(path, handler, web_method, **handler_kwargs)


def create_all_view_handler_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    class Handler(web.View):
        async def _dynamic_method(self) -> handler_return_type:
            return return_value

    setattr(Handler, web_method, Handler._dynamic_method)

    app_with_routes_as_method = create_view_supported_apps(path, Handler, web_method, **handler_kwargs)
    app_with_routes_as_view = create_view_supported_apps(path, Handler, 'view', **handler_kwargs)
    return *app_with_routes_as_method, *app_with_routes_as_view


def create_all_controller_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    from rapidy.routing.http import routers

    class Handler1:
        @_get_bound_method_by_http_method_name(routers, web_method)(**handler_kwargs)
        async def method(self) -> handler_return_type:
            return return_value

    class Handler2:
        @_get_bound_method_by_http_method_name(routers, web_method)(**handler_kwargs)
        async def method(self) -> handler_return_type:
            return return_value

    # FIXME: is used 2 because rapidy accidentally mutates Handler
    app1 = Rapidy(http_route_handlers=[controller(path)(Handler1)])
    app2 = Rapidy(http_route_handlers=[controller.reg(path, Handler2)])
    return app1, app2


def create_middleware_handler_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> Tuple[web.Application, ...]:
    async def handler() -> None:
        pass

    @web.middleware(**handler_kwargs)
    async def middleware(request: web.Request, handler: Callable[[Any], Awaitable[Any]]) -> handler_return_type:
        return return_value

    method = _get_bound_method_by_http_method_name(web, web_method)

    application = web.Application(middlewares=[middleware])
    application.add_routes([method(path, handler)])

    return (application,)


app_fabrics: Tuple[AppFabric, ...] = (
    create_all_function_handler_apps,
    create_all_view_handler_apps,
    create_middleware_handler_apps,
    create_all_controller_apps,
)


async def check_fabric(
    app_fabric: AppFabric,
    web_method_name: str,
    check_return_value: bool = True,
    *,
    # client
    aiohttp_client: AiohttpClient,
    aiohttp_client_response_body_attr_name: ClientBodyExtractMethod = ClientBodyExtractMethod.json,
    aiohttp_client_send_path: str,
    # handler factories attrs
    handler_path: str,
    handler_return_type: Any,
    handler_return_value: Any | None = None,
    expected_return_value: Any = DEFAULT_RETURN_VALUE,
    expected_status_code: int,
    **handler_kwargs: Any,
) -> None:
    all_app_types = app_fabric(
        path=handler_path,
        handler_return_type=handler_return_type,
        web_method=web_method_name,
        return_value=handler_return_value,
        **handler_kwargs,
    )
    for app in all_app_types:
        client = await aiohttp_client(app)
        client_method = _get_bound_method_by_http_method_name(client, web_method_name)

        resp = await client_method(aiohttp_client_send_path)
        assert resp.status == expected_status_code, (resp.status, expected_status_code)
        if check_return_value and handler_return_value is not None:
            resp_data = await getattr(resp, aiohttp_client_response_body_attr_name)()
            assert resp_data == expected_return_value, (resp_data, expected_return_value)


async def check_handlers(
    check_return_value: bool = True,
    expected_return_value: Any = DEFAULT_RETURN_VALUE,
    expected_status_code: int = HTTPStatus.OK,
    *,
    # client
    aiohttp_client: AiohttpClient,
    aiohttp_client_response_body_attr_name: ClientBodyExtractMethod = ClientBodyExtractMethod.json,
    aiohttp_client_send_path: str = '/',
    # handler factories attrs
    status_code: int = HTTPStatus.OK,
    handler_path: str = '/',
    handler_return_type: Any = DEFAULT_RETURN_TYPE,
    handler_return_value: Any | None = DEFAULT_RETURN_VALUE,
    # handler attrs
    response_validate: bool = True,
    response_type: Type[Any] | None | UnsetType = Unset,
    response_content_type: str | ContentType | None = None,
    response_charset: str | Charset = Charset.utf8,
    response_zlib_executor: Executor | None = None,
    response_zlib_executor_size: int | None = None,
    response_include_fields: Include | None = None,
    response_exclude_fields: Exclude | None = None,
    response_by_alias: bool = True,
    response_exclude_unset: bool = False,
    response_exclude_defaults: bool = False,
    response_exclude_none: bool = False,
    response_custom_encoder: CustomEncoder | None = None,
    response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
) -> None:
    for web_method_name in WEB_METHOD_NAMES:
        for app_fabric in app_fabrics:
            await check_fabric(
                app_fabric=app_fabric,
                web_method_name=web_method_name,
                check_return_value=check_return_value,
                # client
                aiohttp_client=aiohttp_client,
                aiohttp_client_response_body_attr_name=aiohttp_client_response_body_attr_name,
                aiohttp_client_send_path=aiohttp_client_send_path,
                # handler factories attrs
                status_code=status_code,
                handler_path=handler_path,
                handler_return_type=handler_return_type,
                handler_return_value=handler_return_value,
                expected_return_value=expected_return_value,
                expected_status_code=expected_status_code,
                # handler attrs
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


async def check_handlers_all_response_models(
    check_return_value: bool = True,
    expected_return_value: Any = DEFAULT_RETURN_VALUE,
    expected_status_code: int = HTTPStatus.OK,
    *,
    # client
    aiohttp_client: AiohttpClient,
    aiohttp_client_response_body_attr_name: ClientBodyExtractMethod = ClientBodyExtractMethod.text,
    aiohttp_client_send_path: str = '/',
    # handler factories attrs
    status_code: int = HTTPStatus.OK,
    handler_path: str = '/',
    handler_return_type: Any = DEFAULT_RETURN_TYPE,
    handler_return_value: Any | None = DEFAULT_RETURN_VALUE,
    # handler attrs
    response_validate: bool = True,
    response_content_type: str | ContentType | None = None,
    response_charset: str | Charset = Charset.utf8,
    response_zlib_executor: Executor | None = None,
    response_zlib_executor_size: int | None = None,
    response_include_fields: Include | None = None,
    response_exclude_fields: Exclude | None = None,
    response_by_alias: bool = True,
    response_exclude_unset: bool = False,
    response_exclude_defaults: bool = False,
    response_exclude_none: bool = False,
    response_custom_encoder: CustomEncoder | None = None,
    response_json_encoder: JSONEncoder = DEFAULT_JSON_ENCODER,
) -> None:
    for attr_name in ('handler_return_type', 'response_type'):
        await check_handlers(
            check_return_value=check_return_value,
            # client
            aiohttp_client=aiohttp_client,
            aiohttp_client_response_body_attr_name=aiohttp_client_response_body_attr_name,
            aiohttp_client_send_path=aiohttp_client_send_path,
            # handler factories attrs
            status_code=status_code,
            handler_path=handler_path,
            handler_return_value=handler_return_value,
            expected_return_value=expected_return_value,
            expected_status_code=expected_status_code,
            **{attr_name: handler_return_type},
            # handler attrs
            response_validate=response_validate,
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
