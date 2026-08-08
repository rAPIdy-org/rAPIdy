import inspect
from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated

import pytest
from rapidy_core.parameters.http import Body

from rapidy import Rapidy
from rapidy.endpoint_handlers.http.attrs_extractor import RequestFieldAlreadyExistsError
from rapidy.http import (
    post as post_route,
    Request,
)
from tests.ported.client import AppClientFactory


async def only_untyped_request_handler(request) -> None:  # type: ignore[no-untyped-def]
    pass


async def without_request_handler(username: Annotated[Any, Body()]) -> None:
    pass


async def with_request_fst_handler(request: Request, username: Annotated[Any, Body()]) -> None:
    pass


async def with_request_snd_handler(username: Annotated[Any, Body()], request: Request) -> None:
    pass


async def with_request_different_name_handler(any_req: Request, username: Annotated[Any, Body()]) -> None:
    pass


@pytest.mark.parametrize(
    'handler',
    [
        only_untyped_request_handler,
        without_request_handler,
        with_request_fst_handler,
        with_request_snd_handler,
        with_request_different_name_handler,
    ],
)
async def test_success(app_client: AppClientFactory, *, handler: Any) -> None:
    app = Rapidy(http_route_handlers=[post_route.reg('/', handler)])

    client = await app_client(app)
    resp = await client.post('/', json={'username': 'username'})

    assert resp.status == HTTPStatus.OK


@pytest.mark.parametrize(
    'attr1_type, attr2_type',
    [
        (inspect.Signature.empty, Request),
        (Request, Request),
    ],
)
async def test_request_defined_twice(attr1_type: Any, attr2_type: Any) -> None:
    async def post(_: attr1_type, __: attr2_type) -> None:
        pass

    with pytest.raises(RequestFieldAlreadyExistsError):
        Rapidy(http_route_handlers=[post_route.reg('/', post)])
