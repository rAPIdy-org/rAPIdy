"""Pydantic models for OpenAPI schema."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class OpenAPIContact(BaseModel):
    """Contact information for the exposed API."""
    name: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class OpenAPILicense(BaseModel):
    """License information for the exposed API."""
    name: str
    url: Optional[str] = None


class OpenAPIInfo(BaseModel):
    """General information about the API."""
    title: str
    version: str
    description: Optional[str] = None
    terms_of_service: Optional[str] = Field(None, alias="termsOfService")
    contact: Optional[OpenAPIContact] = None
    license: Optional[OpenAPILicense] = None


class OpenAPIExample(BaseModel):
    """Example object for request/response."""
    summary: Optional[str] = None
    description: Optional[str] = None
    value: Any = None
    external_value: Optional[str] = Field(None, alias="externalValue")


class OpenAPIReference(BaseModel):
    """Reference to another component in the specification."""
    ref: str = Field(..., alias="$ref")


class OpenAPISchema(BaseModel):
    """Schema object for request/response bodies."""
    title: Optional[str] = None
    type: Optional[str] = None
    format: Optional[str] = None
    items: Optional[Union[OpenAPISchema, OpenAPIReference]] = None
    properties: Optional[Dict[str, Union[OpenAPISchema, OpenAPIReference]]] = None
    required: Optional[List[str]] = None
    description: Optional[str] = None
    default: Any = None
    nullable: Optional[bool] = None
    discriminator: Optional[Dict[str, Any]] = None
    example: Any = None
    deprecated: Optional[bool] = None
    
    class Config:
        extra = "allow"


class OpenAPIParameter(BaseModel):
    """Parameter object for path, query, header and cookie parameters."""
    name: str
    in_: str = Field(..., alias="in")
    description: Optional[str] = None
    required: Optional[bool] = None
    deprecated: Optional[bool] = None
    allow_empty_value: Optional[bool] = Field(None, alias="allowEmptyValue")
    style: Optional[str] = None
    explode: Optional[bool] = None
    schema_: Optional[Union[OpenAPISchema, OpenAPIReference]] = Field(None, alias="schema")
    example: Any = None
    examples: Optional[Dict[str, Union[OpenAPIExample, OpenAPIReference]]] = None


class OpenAPIRequestBody(BaseModel):
    """Request body object."""
    description: Optional[str] = None
    content: Dict[str, Dict[str, Any]]
    required: Optional[bool] = None


class OpenAPIResponse(BaseModel):
    """Response object."""
    description: str
    headers: Optional[Dict[str, Union[OpenAPIParameter, OpenAPIReference]]] = None
    content: Optional[Dict[str, Dict[str, Any]]] = None
    links: Optional[Dict[str, Any]] = None


class OpenAPIOperation(BaseModel):
    """Operation object for path items."""
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    external_docs: Optional[Dict[str, Any]] = Field(None, alias="externalDocs")
    operation_id: Optional[str] = Field(None, alias="operationId")
    parameters: Optional[List[Union[OpenAPIParameter, OpenAPIReference]]] = None
    request_body: Optional[Union[OpenAPIRequestBody, OpenAPIReference]] = Field(
        None, alias="requestBody"
    )
    responses: Dict[str, Union[OpenAPIResponse, OpenAPIReference]]
    deprecated: Optional[bool] = None
    security: Optional[List[Dict[str, List[str]]]] = None
    servers: Optional[List[Dict[str, Any]]] = None


class OpenAPIComponents(BaseModel):
    """Components object for reusable objects."""
    schemas: Optional[Dict[str, Union[OpenAPISchema, OpenAPIReference]]] = None
    responses: Optional[Dict[str, Union[OpenAPIResponse, OpenAPIReference]]] = None
    parameters: Optional[Dict[str, Union[OpenAPIParameter, OpenAPIReference]]] = None
    examples: Optional[Dict[str, Union[OpenAPIExample, OpenAPIReference]]] = None
    request_bodies: Optional[Dict[str, Union[OpenAPIRequestBody, OpenAPIReference]]] = Field(
        None, alias="requestBodies"
    )
    headers: Optional[Dict[str, Union[OpenAPIParameter, OpenAPIReference]]] = None
    security_schemes: Optional[Dict[str, Any]] = Field(None, alias="securitySchemes")
    links: Optional[Dict[str, Any]] = None
    callbacks: Optional[Dict[str, Dict[str, Any]]] = None


class OpenAPISpec(BaseModel):
    """Root document object for OpenAPI specification."""
    openapi: str = "3.0.3"
    info: OpenAPIInfo
    paths: Dict[str, Dict[str, OpenAPIOperation]]
    components: Optional[OpenAPIComponents] = None
    security: Optional[List[Dict[str, List[str]]]] = None
    tags: Optional[List[Dict[str, Any]]] = None
    external_docs: Optional[Dict[str, Any]] = Field(None, alias="externalDocs")
    servers: Optional[List[Dict[str, Any]]] = None 