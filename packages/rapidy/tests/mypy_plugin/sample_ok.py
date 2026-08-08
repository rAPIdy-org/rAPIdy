from __future__ import annotations

from typing import Annotated

from rapidy.http import Body, QueryParam


def consume_int(value: int) -> None:
    pass


async def endpoint(
    body: Annotated[int, Body()],
    query: int = QueryParam(),
) -> None:
    consume_int(body)
    consume_int(query)
