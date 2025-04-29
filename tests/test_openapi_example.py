"""Example test demonstrating OpenAPI functionality with a complete API."""

from typing import Annotated, Dict, List, Optional

import pytest
from pydantic import BaseModel, Field

from rapidy.web_app import Application
from rapidy.openapi.models import OpenAPISpec
from rapidy.parameters.http import Body, PathParam, QueryParam
from rapidy.web import get, post, put, delete


class TodoItem(BaseModel):
    """A todo item."""
    id: Optional[int] = None
    title: str = Field(..., description="The title of the todo item")
    description: Optional[str] = Field(None, description="A detailed description of the todo item")
    completed: bool = Field(False, description="Whether the todo item is completed")


class TodoCreate(BaseModel):
    """Data for creating a todo item."""
    title: str = Field(..., description="The title of the todo item")
    description: Optional[str] = Field(None, description="A detailed description of the todo item")


class TodoUpdate(BaseModel):
    """Data for updating a todo item."""
    title: Optional[str] = Field(None, description="The new title of the todo item")
    description: Optional[str] = Field(None, description="The new description of the todo item")
    completed: Optional[bool] = Field(None, description="The new completion status")


@pytest.fixture
def todo_app():
    """Create a test todo application with OpenAPI documentation."""
    app = Application(
        title="Todo API",
        version="1.0.0",
        description="A simple todo API demonstrating OpenAPI integration"
    )

    # In-memory storage for todos
    todos: Dict[int, TodoItem] = {}
    next_id = 1

    @app.get("/todos")
    async def list_todos(
        skip: Annotated[int, QueryParam(description="Number of items to skip")] = 0,
        limit: Annotated[int, QueryParam(description="Maximum number of items to return")] = 10,
        completed: Annotated[Optional[bool], QueryParam(description="Filter by completion status")] = None,
    ) -> List[TodoItem]:
        """List all todo items.
        
        Returns a paginated list of todo items, optionally filtered by completion status.
        """
        items = list(todos.values())
        if completed is not None:
            items = [item for item in items if item.completed == completed]
        return items[skip:skip + limit]

    @app.get("/todos/{todo_id}")
    async def get_todo(
        todo_id: Annotated[int, PathParam(description="The ID of the todo item to retrieve")],
    ) -> TodoItem:
        """Get a specific todo item by ID.
        
        Returns the todo item with the specified ID.
        """
        if todo_id not in todos:
            raise KeyError(f"Todo item {todo_id} not found")
        return todos[todo_id]

    @app.post("/todos")
    async def create_todo(
        todo: Annotated[TodoCreate, Body(description="The todo item to create")],
    ) -> TodoItem:
        """Create a new todo item.
        
        Creates a new todo item and returns it with an assigned ID.
        """
        nonlocal next_id
        item = TodoItem(
            id=next_id,
            title=todo.title,
            description=todo.description,
        )
        todos[next_id] = item
        next_id += 1
        return item

    @app.put("/todos/{todo_id}")
    async def update_todo(
        todo_id: Annotated[int, PathParam(description="The ID of the todo item to update")],
        update: Annotated[TodoUpdate, Body(description="The fields to update")],
    ) -> TodoItem:
        """Update a todo item.
        
        Updates the specified fields of a todo item and returns the updated item.
        """
        if todo_id not in todos:
            raise KeyError(f"Todo item {todo_id} not found")
        
        item = todos[todo_id]
        if update.title is not None:
            item.title = update.title
        if update.description is not None:
            item.description = update.description
        if update.completed is not None:
            item.completed = update.completed
        return item

    @app.delete("/todos/{todo_id}")
    async def delete_todo(
        todo_id: Annotated[int, PathParam(description="The ID of the todo item to delete")],
    ) -> Dict[str, str]:
        """Delete a todo item.
        
        Deletes the todo item with the specified ID.
        """
        if todo_id not in todos:
            raise KeyError(f"Todo item {todo_id} not found")
        del todos[todo_id]
        return {"message": f"Todo item {todo_id} deleted"}

    return app


async def test_todo_api_workflow(aiohttp_client, todo_app):
    """Test the complete todo API workflow with OpenAPI documentation."""
    client = await aiohttp_client(todo_app)

    # Check OpenAPI schema
    resp = await client.get("/openapi.json")
    assert resp.status == 200
    data = await resp.json()
    spec = OpenAPISpec(**data)

    # Verify API metadata
    assert spec.info.title == "Todo API"
    assert spec.info.version == "1.0.0"
    assert "simple todo API" in spec.info.description

    # Verify endpoints
    assert "/todos" in spec.paths
    assert "/todos/{todo_id}" in spec.paths

    # Test API functionality
    # Create a todo
    resp = await client.post("/todos", json={
        "title": "Test todo",
        "description": "Test description"
    })
    assert resp.status == 200
    todo = await resp.json()
    assert todo["title"] == "Test todo"
    assert todo["description"] == "Test description"
    assert not todo["completed"]
    todo_id = todo["id"]

    # Get the todo
    resp = await client.get(f"/todos/{todo_id}")
    assert resp.status == 200
    todo = await resp.json()
    assert todo["title"] == "Test todo"

    # Update the todo
    resp = await client.put(f"/todos/{todo_id}", json={
        "completed": True
    })
    assert resp.status == 200
    todo = await resp.json()
    assert todo["completed"]

    # List todos
    resp = await client.get("/todos")
    assert resp.status == 200
    todos = await resp.json()
    assert len(todos) == 1
    assert todos[0]["id"] == todo_id

    # Delete the todo
    resp = await client.delete(f"/todos/{todo_id}")
    assert resp.status == 200
    message = await resp.json()
    assert "deleted" in message["message"]

    # Verify todo is deleted
    resp = await client.get("/todos")
    assert resp.status == 200
    todos = await resp.json()
    assert len(todos) == 0


async def test_openapi_ui_endpoints(aiohttp_client, todo_app):
    """Test that Swagger UI and ReDoc endpoints are available."""
    client = await aiohttp_client(todo_app)

    # Test Swagger UI
    resp = await client.get("/docs")
    assert resp.status == 200
    text = await resp.text()
    assert "swagger-ui" in text.lower()

    # Test ReDoc
    resp = await client.get("/redoc")
    assert resp.status == 200
    text = await resp.text()
    assert "redoc" in text.lower() 