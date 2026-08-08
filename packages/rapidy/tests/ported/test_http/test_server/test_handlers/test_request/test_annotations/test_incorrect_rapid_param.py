from http import HTTPStatus
from typing_extensions import Annotated

import pytest
from rapidy_core.fields.model_fields import ModelFieldCreationError
from rapidy_core.parameters.http import Body

from rapidy import Rapidy
from rapidy.http import post
from tests.ported.client import AppClientFactory


async def test_not_injected_param(app_client: AppClientFactory) -> None:
    async def handler(_: Annotated[str, str]) -> None:
        pass

    app = Rapidy(http_route_handlers=[post.reg('/', handler)])

    client = await app_client(app)
    resp = await client.post('/', json={'attr': ''})

    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_unsupported_pydantic_type() -> None:
    class Data:
        pass

    async def handler1(_: Data = Body()) -> None:
        pass

    async def handler2(_: Annotated[Data, Body()]) -> None:
        pass

    for handler in [handler1, handler2]:
        with pytest.raises(ModelFieldCreationError):
            Rapidy(http_route_handlers=[post.reg('/', handler)])  # type: ignore[arg-type]
