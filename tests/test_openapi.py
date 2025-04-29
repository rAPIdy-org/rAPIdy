"""Tests for OpenAPI functionality."""

from typing import Annotated, List, cast

import pytest
from pydantic import BaseModel

from rapidy.web_app import Application
from rapidy.openapi.models import (
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIReference,
    OpenAPISpec
)
from rapidy.parameters.http import Body, PathParam, QueryParam
from rapidy.http import get, post


class Item(BaseModel):
    """Test item model."""
    id: int
    name: str
    description: str | None = None


@pytest.fixture
def app():
    """Create test application."""
    return Application(
        title="Test API",
        version="1.0.0",
        description="Test API description"
    )


@pytest.fixture
def _test_app(app):
    """Create test application with routes."""
    @get("/items")
    async def get_items(
        skip: Annotated[int, QueryParam()] = 0,
        limit: Annotated[int, QueryParam()] = 10
    ) -> List[Item]:
        """Get list of items.
        
        Returns a paginated list of items.
        """
        return []

    @get("/items/{item_id}")
    async def get_item(item_id: Annotated[int, PathParam()]) -> Item:
        """Get an item by ID.
        
        Returns a single item from the database.
        """
        return Item(id=item_id, name="test")

    @post("/items")
    async def create_item(item: Annotated[Item, Body()]) -> Item:
        """Create a new item.
        
        Creates a new item in the database.
        """
        return item

    app.add_http_routers([get_items, get_item, create_item])

    return app


async def test_openapi_json(aiohttp_client, _test_app):
    """Test /openapi.json endpoint."""
    client = await aiohttp_client(_test_app)
    resp = await client.get("/openapi.json")
    assert resp.status == 200
    
    data = await resp.json()
    spec = OpenAPISpec(**data)
    
    # Check basic info
    assert spec.info.title == "Test API"
    assert spec.info.version == "1.0.0"
    assert spec.info.description == "Test API description"
    
    # Check paths
    assert "/items" in spec.paths
    assert "/items/{item_id}" in spec.paths
    
    # Check GET /items
    items_get = spec.paths["/items"]["get"]
    assert isinstance(items_get, OpenAPIOperation)
    assert items_get.summary == "Get list of items."
    assert items_get.parameters is not None
    assert len(items_get.parameters) == 2
    assert items_get.responses["200"].content is not None
    assert items_get.responses["200"].content["application/json"]["schema"]["type"] == "array"
    
    # Check GET /items/{item_id}
    item_get = spec.paths["/items/{item_id}"]["get"]
    assert isinstance(item_get, OpenAPIOperation)
    assert item_get.summary == "Get an item by ID."
    assert item_get.parameters is not None
    assert len(item_get.parameters) == 1
    param = item_get.parameters[0]
    assert isinstance(param, OpenAPIParameter)
    assert param.name == "item_id"
    assert param.in_ == "path"
    assert param.required is True
    
    # Check POST /items
    item_post = spec.paths["/items"]["post"]
    assert isinstance(item_post, OpenAPIOperation)
    assert item_post.summary == "Create a new item."
    assert item_post.request_body is not None
    assert "application/json" in item_post.request_body.content


async def test_swagger_ui(aiohttp_client, _test_app):
    """Test /docs endpoint."""
    client = await aiohttp_client(_test_app)
    resp = await client.get("/docs")
    assert resp.status == 200
    assert "text/html" in resp.headers["content-type"]
    
    text = await resp.text()
    assert "swagger-ui" in text
    assert "SwaggerUIBundle" in text


async def test_redoc(aiohttp_client, _test_app):
    """Test /redoc endpoint."""
    client = await aiohttp_client(_test_app)
    resp = await client.get("/redoc")
    assert resp.status == 200
    assert "text/html" in resp.headers["content-type"]
    
    text = await resp.text()
    assert "redoc" in text
    assert "Redoc.init" in text 