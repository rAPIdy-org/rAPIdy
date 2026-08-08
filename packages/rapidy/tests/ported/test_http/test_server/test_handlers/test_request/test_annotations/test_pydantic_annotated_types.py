from typing import Any
from typing_extensions import Annotated
from uuid import UUID, uuid4

import pytest
from pydantic import UUID4

from rapidy import Rapidy
from rapidy.http import PathParam, post
from tests.ported.client import AppClientFactory


def check_uuid4(test_uuid: Any) -> bool:
    if not isinstance(test_uuid, UUID):
        return False

    return test_uuid.version == 4


async def annotated_def_handler(user_id: Annotated[UUID4, PathParam()]) -> None:
    assert check_uuid4(user_id)


async def default_def_handler(user_id: UUID4 = PathParam()) -> None:
    assert check_uuid4(user_id)


@pytest.mark.parametrize(
    'handler',
    [
        annotated_def_handler,
        default_def_handler,
    ],
)
async def test_pydantic_annotated(app_client: AppClientFactory, handler: Any) -> None:
    app = Rapidy(http_route_handlers=[post.reg('/{user_id}', handler)])
    client = await app_client(app)

    resp = await client.post(f'/{uuid4()}')
    assert resp.status == 200
