"""Utility functions for OpenAPI schema generation."""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Type, Union, get_args, get_origin, TYPE_CHECKING

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from rapidy.openapi.models import (
    OpenAPIComponents,
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIReference,
    OpenAPIRequestBody,
    OpenAPIResponse,
    OpenAPISchema,
)
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
from rapidy.web_request import Request
from rapidy.web_response import Response

if TYPE_CHECKING:
    from rapidy.web_app import Application


def get_type_schema(
    python_type: Any,
    components: Optional[OpenAPIComponents] = None,
    by_alias: bool = True,
) -> Union[OpenAPISchema, OpenAPIReference]:
    """Convert a Python type to an OpenAPI Schema object."""
    if components is None:
        components = OpenAPIComponents()
    
    if components.schemas is None:
        components.schemas = {}

    # Handle None
    if python_type is None:
        return OpenAPISchema(type="null")

    # Handle basic types
    if python_type is str:
        return OpenAPISchema(type="string")
    elif python_type is int:
        return OpenAPISchema(type="integer")
    elif python_type is float:
        return OpenAPISchema(type="number")
    elif python_type is bool:
        return OpenAPISchema(type="boolean")
    elif python_type is dict:
        return OpenAPISchema(type="object")
    elif python_type is list:
        return OpenAPISchema(type="array")

    # Handle Pydantic models
    if inspect.isclass(python_type) and issubclass(python_type, BaseModel):
        return get_model_schema(python_type, components, by_alias)

    # Handle typing.Optional
    origin = get_origin(python_type)
    if origin is Union:
        args = get_args(python_type)
        if len(args) == 2 and args[1] is type(None):  # noqa
            inner_schema = get_type_schema(args[0], components, by_alias)
            if isinstance(inner_schema, OpenAPISchema):
                inner_schema.nullable = True
            return inner_schema

    # Handle typing.List
    if origin is list:
        args = get_args(python_type)
        if args:
            items_schema = get_type_schema(args[0], components, by_alias)
            return OpenAPISchema(type="array", items=items_schema)
        return OpenAPISchema(type="array")

    # Handle typing.Dict
    if origin is dict:
        return OpenAPISchema(type="object")

    # Default to string if type is unknown
    return OpenAPISchema(type="string")


def get_model_schema(
    model: Type[BaseModel],
    components: Optional[OpenAPIComponents] = None,
    by_alias: bool = True,
) -> Union[OpenAPISchema, OpenAPIReference]:
    """Convert a Pydantic model to an OpenAPI Schema object."""
    if components is None:
        components = OpenAPIComponents()
    
    if components.schemas is None:
        components.schemas = {}

    model_name = model.__name__
    if model_name in components.schemas:
        return OpenAPIReference(ref=f"#/components/schemas/{model_name}")

    # Create schema for model
    schema = model.model_json_schema(by_alias=by_alias)
    components.schemas[model_name] = OpenAPISchema(**schema)

    return OpenAPIReference(ref=f"#/components/schemas/{model_name}")


def get_field_schema(
    field: FieldInfo,
    components: Optional[OpenAPIComponents] = None,
    by_alias: bool = True,
) -> Union[OpenAPISchema, OpenAPIReference]:
    """Convert a Pydantic field to an OpenAPI Schema object."""
    if isinstance(field, (PathBase, QueryBase, HeaderBase, CookieBase)):
        schema = get_type_schema(field.annotation, components, by_alias)
        if isinstance(schema, OpenAPISchema):
            if field.description:
                schema.description = field.description
            if field.deprecated:
                schema.deprecated = True
            if field.examples:
                schema.example = field.examples[0]
        return schema

    elif isinstance(field, Body):
        if inspect.isclass(field.annotation) and issubclass(field.annotation, BaseModel):
            return get_model_schema(field.annotation, components, by_alias)
        return get_type_schema(field.annotation, components, by_alias)
    
    return get_type_schema(field.annotation, components, by_alias)


def setup_openapi_routes(
        app: Application,
        title: str,
        version: str,
        description: str,
        openapi_url: str | None,
        docs_url: str | None,
        redoc_url: str | None,
) -> None:
    """Setup OpenAPI documentation routes."""
    from rapidy.http import get, Response

    @get(openapi_url, allow_head=False)
    async def get_openapi_json(request: Request) -> Response:
        """Generate OpenAPI JSON schema."""
        from rapidy.openapi.route import get_openapi_spec
        
        spec = await get_openapi_spec(request.app, title=title, version=version, description=description)
        return Response(spec.model_dump(by_alias=True, exclude_none=True))

    @get(docs_url, allow_head=False)
    async def get_swagger_ui(request: Request) -> Response:
        """Serve Swagger UI."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Swagger UI</title>
            <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script>
                window.onload = () => {{
                    window.ui = SwaggerUIBundle({{
                        url: '{request.url.parent / "openapi.json"}',
                        dom_id: '#swagger-ui',
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIBundle.SwaggerUIStandalonePreset
                        ],
                        layout: "BaseLayout",
                        deepLinking: true
                    }})
                }}
            </script>
        </body>
        </html>
        """
        return Response(text=html, content_type="text/html")

    @get(redoc_url, allow_head=False)
    async def get_redoc(request: Request) -> Response:
        """Serve ReDoc."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ReDoc</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
        </head>
        <body>
            <div id="redoc"></div>
            <script>
                Redoc.init('{request.url.parent / "openapi.json"}', {{
                    scrollYOffset: 50
                }}, document.getElementById('redoc'))
            </script>
        </body>
        </html>
        """
        return Response(text=html, content_type="text/html")

    if openapi_url:
        app.add_http_router(get_openapi_json)

    if docs_url:
        app.add_http_router(get_swagger_ui)

    if redoc_url:
        app.add_http_router(get_redoc)
