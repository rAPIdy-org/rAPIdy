from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import UUID4
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import web


def check_uuid4(test_uuid: Any) -> bool:
    if not isinstance(test_uuid, UUID):
        return False

    return test_uuid.version == 4


async def annotated_def_handler(user_id: Annotated[UUID4, web.PathParam()]) -> None:
    assert check_uuid4(user_id)


async def default_def_handler(user_id: UUID4 = web.PathParam()) -> None:
    assert check_uuid4(user_id)


@pytest.mark.parametrize(
    'handler', [
        annotated_def_handler,
        default_def_handler,
    ],
)
async def test_pydantic_annotated(aiohttp_client: AiohttpClient, handler: Any) -> None:
    app = web.Application()

    app.add_routes([web.post('/{user_id}', handler)])
    client = await aiohttp_client(app)

    resp = await client.post(f'/{uuid4()}')
    assert resp.status == 200
