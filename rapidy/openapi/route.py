"""Functions for extracting OpenAPI information from route handlers."""


import inspect
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints, Annotated, TYPE_CHECKING, TypeAlias
from unittest.mock import MagicMock

from pydantic import BaseModel
from yarl import URL

from rapidy.annotation_checkers import is_optional
from rapidy.endpoint_handlers.attr_extractor import get_handler_raw_info
from rapidy.endpoint_handlers.http.attrs_extractor import get_http_handler_info
from rapidy.fields.field_info import RapidyFieldInfo
from rapidy.openapi.models import (
    OpenAPIComponents,
    OpenAPIInfo,
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIRequestBody,
    OpenAPIResponse,
    OpenAPISchema,
    OpenAPISpec,
)
from rapidy.openapi.utils import get_field_schema, get_type_schema
from rapidy.parameters.http import (
    Body,
    Cookie,
    CookieBase,
    Header,
    HeaderBase,
    PathParam,
    PathBase,
    QueryParam,
    QueryBase,
)
from rapidy.typedefs import Required, Undefined, Middleware

from rapidy.web_request import Request
from rapidy.web_response import Response

from aiohttp.web_urldispatcher import PrefixedSubAppResource, ResourceRoute

if TYPE_CHECKING:
    from rapidy.web_app import Application

AppID: TypeAlias = int
MiddlewareParams: TypeAlias = list[OpenAPIParameter]


def create_openapi_parameter(  # TODO?
        param_name: str,
        field_info: RapidyFieldInfo,
        components: OpenAPIComponents,
) -> OpenAPIParameter:
    not_default = field_info.default in (Required, Undefined) and field_info.default_factory is None
    required = not_default and not is_optional(field_info.annotation)

    name = field_info.alias or param_name

    if isinstance(field_info, PathBase):
        return OpenAPIParameter(
            name=name,
            in_="path",
            required=True,
            schema_=get_field_schema(field_info, components),
        )

    if isinstance(field_info, QueryBase):
        return OpenAPIParameter(
            name=name,
            in_="query",
            required=required,
            schema_=get_field_schema(field_info, components),
        )

    if isinstance(field_info, HeaderBase):
        return OpenAPIParameter(
            name=name,
            in_="header",
            required=required,
            schema_=get_field_schema(field_info, components),
        )

    if isinstance(field_info, CookieBase):
        return OpenAPIParameter(
            name=name,
            in_="cookie",
            required=required,
            schema_=get_field_schema(field_info, components),
        )

    raise


def get_openapi_operation(
    handler: Any,
    path: str,  # TODO:
    method: str,  # TODO:
    additional_parameters: list[OpenAPIParameter],
    components: Optional[OpenAPIComponents] = None,
) -> OpenAPIOperation:
    """Extract OpenAPI Operation object from a route handler."""
    if components is None:
        components = OpenAPIComponents()

    handler_raw_info = get_http_handler_info(
        handler=handler,
        request_attr_can_declare_fst=False,  # TODO: абсолютно похуй че там с реквестом, может на подфункцию вынести полукчение http_аттрибутов
    )

    parameters: List[OpenAPIParameter] = []
    request_body: Optional[OpenAPIRequestBody] = None

    parameters.extend(additional_parameters)  # TODO: ...

    for request_attr in handler_raw_info.request_params:
        param_name = request_attr.attribute_name
        field_info = request_attr.field_info

        # TODO: required потом на отдельную проверку херануть тк юзается в 2х местах
        not_default = field_info.default in (Required, Undefined) and field_info.default_factory is None
        required = not_default and not is_optional(field_info.annotation)

        if isinstance(field_info, Body):
            request_body = OpenAPIRequestBody(
                required=required,
                content={
                    "application/json": {
                        "schema": get_field_schema(field_info, components),
                    }
                },
            )
        else:
            openapi_param = create_openapi_parameter(
                param_name=param_name, field_info=field_info, components=components,
            )
            parameters.append(openapi_param)

    # Get response schema
    return_type = handler_raw_info.return_annotation
    responses: Dict[str, OpenAPIResponse] = {}

    if return_type and return_type is not None:
        try:
            is_response = inspect.isclass(return_type) and issubclass(return_type, Response)
        except TypeError:
            is_response = False

        if is_response:
            # Use status code from handler kwargs or default to 200
            status_code = getattr(handler, "status_code", 200)
            responses[str(status_code)] = OpenAPIResponse(
                description="Successful response",
                content={
                    "application/json": {
                        "schema": OpenAPISchema(type="object"),
                    }
                },
            )
        else:
            responses["200"] = OpenAPIResponse(
                description="Successful response",
                content={
                    "application/json": {
                        "schema": get_type_schema(return_type, components),
                    }
                },
            )

    # Get operation metadata
    operation = OpenAPIOperation(
        summary=handler.__doc__.split("\n")[0] if handler.__doc__ else None,
        description=handler.__doc__ if handler.__doc__ else None,
        parameters=parameters or None,
        request_body=request_body,
        responses=responses,
        deprecated=getattr(handler, "deprecated", None),  # TODO
        tags=getattr(handler, "tags", None),  # TODO
    )

    return operation


def get_openapi_path(  # TODO? что это вообще за ручка?
    path: str,
    handlers: Dict[str, Any],
    components: Optional[OpenAPIComponents] = None,
) -> Dict[str, OpenAPIOperation]:
    """Extract OpenAPI Path Item object from route handlers."""
    operations: Dict[str, OpenAPIOperation] = {}

    for method, handler in handlers.items():
        method = method.lower()
        if method == "head":
            # Skip HEAD methods as they're handled by GET
            continue
        operations[method] = get_openapi_operation(
            handler=handler,
            path=path,
            method=method,
            additional_parameters=additional_parameters,
            components=components,
        )

    return operations


async def get_openapi_spec(app: 'Application', title: str, version: str, description: str) -> OpenAPISpec:
    """Generate OpenAPI specification from application routes."""
    components = OpenAPIComponents()
    paths: Dict[str, Dict[str, OpenAPIOperation]] = {}
    # TODO: миддлвари - как с них извлекать

    core_middlewares = app.middlewares
    additional_m_params: dict[AppID, MiddlewareParams] = {}

    # Group handlers by path
    for route in app.router.routes():
        if not hasattr(route, "handler"):  # TODO:
            continue

        # middlewares = get_route_middlewares(route)

        # resource = route.resource
        # request = Request()

        app_ids_for_handler: set[AppID] = set()

        method = route.method.lower()
        path = route.resource.canonical

        request = MagicMock()
        request.method = method
        request.rel_url = URL(route.resource.canonical)

        match_info = await app.router.resolve(request)
        # TODO: также еще надо парсить схемы Header, Cookie и тп чтобы достать из них одиночные параметры
        for sub_app in match_info.apps:  # TODO: рутовое приложение тоже учитывается?
            # TODO: повыводить ворнинги если не удастся спарсить миддлвару или она не рапидовская
            #  но есть же еще системныве ...
            for app in match_info.apps[::-1]:
                app_ids_for_handler.add(id(app))

                if id(app) in additional_m_params:
                    continue  # недопускаем попвторных просчетов параметров

                for m, new_style in app._middlewares_handlers:
                    handler_raw_info = get_http_handler_info(
                        handler=m,
                        request_attr_can_declare_fst=False,
                        # TODO: абсолютно похуй че там с реквестом, может на подфункцию вынести полукчение http_аттрибутов
                    )

                    for request_attr in handler_raw_info.request_params:
                        if isinstance(request_attr.field_info, Body):
                            pass
                            # request_body = OpenAPIRequestBody(
                            #     required=required,
                            #     content={
                            #         "application/json": {
                            #             "schema": get_field_schema(field_info, components),
                            #         }
                            #     },
                            # )
                        else:
                            openapi_param = create_openapi_parameter(
                                param_name=request_attr.attribute_name,  # TODO: alias тут и везде убедится он или имя
                                field_info=request_attr.field_info,
                                components=components,
                            )
                            additional_m_params[id(app)].append(openapi_param)


        # TODO: если это view достать все методы что у него есть? и пропотрошить? как сделать для view?
        # TODO: view - впринципе не извлекаются

        # TODO: чтобы не возникало дублей если один и тот же параметр извлекаем
        # TODO: легкий механизм добавления примеров



        # TODO: как объединять боди и вообще схемы? миддлвара может требовать одну схему, а хендлер уже будет требовать
        #  расширенную -> как мутить? сливать их как-то используя pydantic?
        #  ->> пока игнорить решить позже отдельной таской?
        
        if path not in paths:
            paths[path] = {}

        additional_parameters = [additional_m_params.get(app_id, ()) for app_id in app_ids_for_handler]  # TODO
        additional_parameters = [item for sublist in additional_parameters for item in sublist]  # TODO

        paths[path][method] = get_openapi_operation(
            handler=route.handler,
            path=path,
            method=method,
            additional_parameters=additional_parameters,
            components=components,
        )

    return OpenAPISpec(
        info=OpenAPIInfo(title=title, version=version, description=description),
        paths=paths,
        components=components,
    )


def get_route_middlewares(route: ResourceRoute) -> List[Middleware]:
    """Extract all middlewares that will be applied for the current route.
    
    Args:
        route (ResourceRoute): The route to get middlewares for.
        
    Returns:
        List[Middleware]: List of middlewares that will be applied for the route.
    """
    middlewares: List[Middleware] = []
    
    # Get application middlewares
    app = getattr(route.resource, '_app', None)
    if app is not None and hasattr(app, 'middlewares'):
        middlewares.extend(app.middlewares)
        
    # Get subapp middlewares if route is in a subapp
    resource = route.resource
    while isinstance(resource, PrefixedSubAppResource):
        subapp = getattr(resource, '_app', None)
        if subapp is not None and hasattr(subapp, 'middlewares'):
            middlewares.extend(subapp.middlewares)
        resource = getattr(resource, '_parent', None)
        if resource is None:
            break
        
    # Get route-specific middleware if any
    handler = route.handler
    if hasattr(handler, '__middleware__'):
        middlewares.append(handler)
        
    return middlewares
