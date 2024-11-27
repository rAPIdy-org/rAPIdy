from http import HTTPStatus

import pytest
from aiohttp.pytest_plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import web
from rapidy.fields.model_fields import ModelFieldCreationError
from rapidy.parameters.http import Body


async def test_not_injected_param(aiohttp_client: AiohttpClient) -> None:
    async def handler(_: Annotated[str, str]) -> None:
        pass

    app = web.Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post('/', json={'attr': ''})

    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_unsupported_pydantic_type() -> None:
    class Data:
        pass

    async def handler1(_: Data = Body()) -> None: pass

    async def handler2(_: Annotated[Data, Body()]) -> None: pass

    app = web.Application()

    for handler in [handler1, handler2]:
        with pytest.raises(ModelFieldCreationError):
            app.add_routes([web.post('/', handler)])  # type: ignore[arg-type]
