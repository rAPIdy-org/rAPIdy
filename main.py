from typing import Annotated

from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse
from pydantic import BaseModel

from rapidy import Rapidy, run_app, web
from rapidy.http import get, post
from rapidy.parameters.http import QueryParam, PathParam, Body
from rapidy.typedefs import CallNext
from rapidy.web_middlewares import middleware


class Item(BaseModel):
    """Test item model."""
    id: int
    name: str
    description: str | None = None


@get("/items")
async def get_items(
        skip: Annotated[int, QueryParam()] = 0,
        limit: Annotated[int, QueryParam()] = 10
) -> list[Item]:
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


class Foo(web.View):
    async def get(self) -> list[str]:
        return []

    async def post(self, item: Annotated[Item, Body()]) -> Item:
        return item

@middleware
async def hello_rapidy_middleware(request: Request, call_next: CallNext) -> StreamResponse:
    print('before')
    handler_response = await call_next(request)
    print('after')
    return handler_response



root_app = Rapidy(
    title="Test API",
    version="1.0.0",
    description="Test API description"
)

root_app.add_http_routers([
    get_items,
    # get_item,
    # create_item
])
root_app.router.add_view('/view', Foo)

v1app = Rapidy(
    middlewares=[hello_rapidy_middleware],
)
v1app.add_http_routers([
    get_item,
    create_item,
])

root_app.add_subapp('/v1', v1app)

if __name__ == "__main__":
    run_app(root_app)


"""
TODO: сохранить ссылки на обработчики
и миддлвары

при продергивании swagger -> ответ рекурсивно собирается по всем энжпойнтам и кешируется?

security schemas с заголовков

определить виды и как вязать для опенапи
"""