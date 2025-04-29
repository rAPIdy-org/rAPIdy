"""Functions for extracting OpenAPI information from route handlers."""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints, Annotated

from pydantic import BaseModel

from rapidy.annotation_checkers import is_optional
from rapidy.endpoint_handlers.attr_extractor import get_handler_raw_info
from rapidy.endpoint_handlers.http.attrs_extractor import get_http_handler_info
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
from rapidy.typedefs import Required, Undefined
from rapidy.web_request import Request
from rapidy.web_response import Response


def get_openapi_operation(
    handler: Any,
    path: str,
    method: str,
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

    for request_attr in handler_raw_info.request_params:
        param_name = request_attr.attribute_name
        field_info = request_attr.field_info

        # TODO: required потом на отдельную проверку херануть тк юзается в 2х местах
        not_default = field_info.default in (Required, Undefined) and field_info.default_factory is None
        required = not_default and not is_optional(field_info.annotation)

        # Handle different parameter types
        if isinstance(field_info, PathBase):
            parameters.append(
                OpenAPIParameter(
                    name=param_name,
                    in_="path",
                    required=True,
                    schema_=get_field_schema(field_info, components),
                )
            )
        elif isinstance(field_info, QueryBase):
            parameters.append(
                OpenAPIParameter(
                    name=param_name,
                    in_="query",
                    required=required,
                    schema_=get_field_schema(field_info, components),
                )
            )
        elif isinstance(field_info, HeaderBase):
            parameters.append(
                OpenAPIParameter(
                    name=param_name,
                    in_="header",
                    required=required,
                    schema_=get_field_schema(field_info, components),
                )
            )
        elif isinstance(field_info, CookieBase):
            parameters.append(
                OpenAPIParameter(
                    name=param_name,
                    in_="cookie",
                    required=required,
                    schema_=get_field_schema(field_info, components),
                )
            )
        elif isinstance(field_info, Body):
            request_body = OpenAPIRequestBody(
                required=required,
                content={
                    "application/json": {
                        "schema": get_field_schema(field_info, components),
                    }
                },
            )

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
        deprecated=getattr(handler, "deprecated", None),
        tags=getattr(handler, "tags", None),
    )

    return operation


def get_openapi_path(
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
            handler,
            path,
            method,
            components,
        )

    return operations


def get_openapi_spec(app: Any) -> OpenAPISpec:
    """Generate OpenAPI specification from application routes."""
    components = OpenAPIComponents()
    paths: Dict[str, Dict[str, OpenAPIOperation]] = {}

    # Group handlers by path
    for route in app.router.routes():
        if not hasattr(route, "handler"):
            continue

        path = route.resource.canonical
        method = route.method.lower()
        
        if path not in paths:
            paths[path] = {}
        
        paths[path][method] = get_openapi_operation(
            route.handler,
            path,
            method,
            components,
        )

    # Create OpenAPI spec
    return OpenAPISpec(
        info=OpenAPIInfo(
            title=getattr(app, "_title", "Rapidy API"),  # TODO
            version=getattr(app, "_version", "0.1.0"),  # TODO
            description=getattr(app, "_description", None),  # TODO
        ),
        paths=paths,
        components=components,
    ) 