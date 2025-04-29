"""OpenAPI schema generation for Rapidy.

This module provides functionality for automatically generating OpenAPI schemas
from Rapidy route handlers and Pydantic models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from rapidy.openapi.models import OpenAPIInfo, OpenAPISchema
from rapidy.openapi.route import get_openapi_path, get_openapi_operation
from rapidy.openapi.utils import (
    get_model_schema,
    get_type_schema,
    setup_openapi_routes
)

__all__ = [
    "OpenAPIInfo",
    "OpenAPISchema",
    "get_openapi_path",
    "get_openapi_operation",
    "get_model_schema",
    "get_type_schema",
    "setup_openapi_routes"
] 