import inspect
from http import HTTPStatus
from typing import Any

import pytest
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import web
from rapidy.endpoint_handlers.http.attrs_extractor import RequestFieldAlreadyExistsError
from rapidy.parameters.http import Body
from rapidy.web import Application


async def only_untyped_request_handler(request) -> None: pass  # type: ignore[no-untyped-def]


async def without_request_handler(username: Annotated[Any, Body()]) -> None: pass


async def with_request_fst_handler(request: web.Request, username: Annotated[Any, Body()]) -> None: pass


async def with_request_snd_handler(username: Annotated[Any, Body()], request: web.Request) -> None: pass


async def with_request_different_name_handler(any_req: web.Request, username: Annotated[Any, Body()]) -> None: pass


@pytest.mark.parametrize(
    'handler', [
        only_untyped_request_handler,
        without_request_handler,
        with_request_fst_handler,
        with_request_snd_handler,
        with_request_different_name_handler,
    ],
)
async def test_success(aiohttp_client: AiohttpClient, *, handler: Any) -> None:
    app = Application()
    app.add_routes([web.post('/', handler)])

    client = await aiohttp_client(app)
    resp = await client.post('/', json={'username': 'username'})

    assert resp.status == HTTPStatus.OK


@pytest.mark.parametrize(
    'attr1_type, attr2_type', [
        (inspect.Signature.empty, web.Request),
        (web.Request, web.Request),
    ],
)
async def test_request_defined_twice(attr1_type: Any, attr2_type: Any) -> None:
    async def post(_: attr1_type, __: attr2_type) -> None: pass

    app = Application()

    with pytest.raises(RequestFieldAlreadyExistsError):
        app.add_routes([web.post('/', post)])
