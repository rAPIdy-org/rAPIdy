from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel

from rapidy import Rapidy
from rapidy.depends import FromDI
from rapidy.http import Body, get, PathParam, post


class Payload(BaseModel):
    value: int


@get('/items/{item_id}')
async def get_item(item_id: Annotated[int, PathParam()]) -> dict[str, int]:
    return {'item_id': item_id}


@post('/items')
async def create_item(payload: Annotated[Payload, Body()], dependency: FromDI[str]) -> Payload:
    dependency.upper()
    return payload


app: Rapidy = Rapidy(http_route_handlers=[get_item, create_item])
