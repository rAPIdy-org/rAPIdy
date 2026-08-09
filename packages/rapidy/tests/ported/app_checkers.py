from concurrent.futures import Executor
from http import HTTPStatus
from typing import Any, Callable

from rapidy_core.encoders import CustomEncoder, Exclude, Include
from rapidy_core.enums import Charset, ContentType

from rapidy import Rapidy
from rapidy.constants import DEFAULT_JSON_ENCODER
from rapidy.http import controller, middleware, Request
from rapidy.routing.http import routers
from rapidy.typedefs import CallNext, JSONEncoder, UNSET, UnsetType, View
from tests.ported.client import AppClientFactory
from tests.ported.constants import ClientBodyExtractMethod, DEFAULT_RETURN_TYPE, DEFAULT_RETURN_VALUE

__all__ = ('AppFabric', 'check_handlers', 'check_handlers_all_response_models')

type AppFabric = Callable[..., tuple[Rapidy, ...]]

WEB_METHOD_NAMES: tuple[str, ...] = ('get', 'post', 'put', 'patch', 'delete', 'options')


def _get_bound_method_by_http_method_name(obj: Any, method_name: str) -> Any:
    return getattr(obj, method_name)


def decorator_method(path: str, handler: Any, web_method: str, **handler_kwargs: Any) -> Rapidy:
    method = _get_bound_method_by_http_method_name(routers, web_method)
    route = method(path, **handler_kwargs)(handler)
    return Rapidy(http_route_handlers=[route])


def decorator_method_reg(path: str, handler: Any, web_method: str, **handler_kwargs: Any) -> Rapidy:
    method = _get_bound_method_by_http_method_name(routers, web_method)
    return Rapidy(http_route_handlers=[method.reg(path, handler, **handler_kwargs)])


def add_http_router_method(path: str, handler: Any, web_method: str, **handler_kwargs: Any) -> Rapidy:
    method = _get_bound_method_by_http_method_name(routers, web_method)
    app = Rapidy()
    app.add_http_router(method.reg(path, handler, **handler_kwargs))
    return app


all_app_def = (decorator_method, decorator_method_reg, add_http_router_method)


def create_all_apps(path: str, handler: Any, web_method: str, **handler_kwargs: Any) -> tuple[Rapidy, ...]:
    return tuple(app_def(path, handler, web_method, **handler_kwargs) for app_def in all_app_def)


def create_all_function_handler_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> tuple[Rapidy, ...]:
    async def handler() -> handler_return_type:
        return return_value

    return create_all_apps(path, handler, web_method, **handler_kwargs)


def create_all_view_handler_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> tuple[Rapidy, ...]:
    class Handler(View):
        async def _dynamic_method(self) -> handler_return_type:
            return return_value

    setattr(Handler, web_method, Handler._dynamic_method)
    decorated = Rapidy(http_route_handlers=[controller(path, **handler_kwargs)(Handler)])
    registered = Rapidy(http_route_handlers=[controller.reg(path, Handler, **handler_kwargs)])
    added = Rapidy()
    added.add_http_router(controller.reg(path, Handler, **handler_kwargs))
    return decorated, registered, added


def create_all_controller_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> tuple[Rapidy, ...]:
    class Handler1:
        @_get_bound_method_by_http_method_name(routers, web_method)(**handler_kwargs)
        async def method(self) -> handler_return_type:
            return return_value

    class Handler2:
        @_get_bound_method_by_http_method_name(routers, web_method)(**handler_kwargs)
        async def method(self) -> handler_return_type:
            return return_value

    app1 = Rapidy(http_route_handlers=[controller(path)(Handler1)])
    app2 = Rapidy(http_route_handlers=[controller.reg(path, Handler2)])
    return app1, app2


def create_middleware_handler_apps(
    path: str,
    handler_return_type: Any,
    web_method: str,
    return_value: Any,
    **handler_kwargs: Any,
) -> tuple[Rapidy, ...]:
    async def handler() -> None:
        pass

    @middleware(**handler_kwargs)
    async def response_middleware(
        request: Request,
        call_next: CallNext,
    ) -> handler_return_type:
        return return_value

    method = _get_bound_method_by_http_method_name(routers, web_method)
    application = Rapidy(
        middlewares=[response_middleware],
        http_route_handlers=[method.reg(path, handler)],
    )
    return (application,)


app_fabrics: tuple[AppFabric, ...] = (
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
    app_client: AppClientFactory,
    client_response_body_attr_name: ClientBodyExtractMethod = ClientBodyExtractMethod.json,
    client_send_path: str,
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
        client = await app_client(app)
        client_method = _get_bound_method_by_http_method_name(client, web_method_name)
        try:
            response = await client_method(client_send_path)
            assert response.status == expected_status_code, (response.status, expected_status_code)
            if check_return_value and handler_return_value is not None:
                response_data = await getattr(response, client_response_body_attr_name)()
                assert response_data == expected_return_value, (response_data, expected_return_value)
        finally:
            await client.close()


async def check_handlers(
    check_return_value: bool = True,
    expected_return_value: Any = DEFAULT_RETURN_VALUE,
    expected_status_code: int = HTTPStatus.OK,
    *,
    app_client: AppClientFactory,
    client_response_body_attr_name: ClientBodyExtractMethod = ClientBodyExtractMethod.json,
    client_send_path: str = '/',
    status_code: int = HTTPStatus.OK,
    handler_path: str = '/',
    handler_return_type: Any = DEFAULT_RETURN_TYPE,
    handler_return_value: Any | None = DEFAULT_RETURN_VALUE,
    response_validate: bool = True,
    response_type: type[Any] | UnsetType | None = UNSET,
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
                app_client=app_client,
                client_response_body_attr_name=client_response_body_attr_name,
                client_send_path=client_send_path,
                status_code=status_code,
                handler_path=handler_path,
                handler_return_type=handler_return_type,
                handler_return_value=handler_return_value,
                expected_return_value=expected_return_value,
                expected_status_code=expected_status_code,
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
    app_client: AppClientFactory,
    client_response_body_attr_name: ClientBodyExtractMethod = ClientBodyExtractMethod.text,
    client_send_path: str = '/',
    status_code: int = HTTPStatus.OK,
    handler_path: str = '/',
    handler_return_type: Any = DEFAULT_RETURN_TYPE,
    handler_return_value: Any | None = DEFAULT_RETURN_VALUE,
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
            app_client=app_client,
            client_response_body_attr_name=client_response_body_attr_name,
            client_send_path=client_send_path,
            status_code=status_code,
            handler_path=handler_path,
            handler_return_value=handler_return_value,
            expected_return_value=expected_return_value,
            expected_status_code=expected_status_code,
            **{attr_name: handler_return_type},
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
