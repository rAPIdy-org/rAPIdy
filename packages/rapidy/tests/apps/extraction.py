from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.http import Body, post, QueryParam


class Item(BaseModel):
    name: str


@post('/items')
async def create_item(item: Item = Body(), quantity: int = QueryParam(alias='q')) -> str:
    return f'{item.name}:{quantity}'


app = Rapidy(http_route_handlers=[create_item])
