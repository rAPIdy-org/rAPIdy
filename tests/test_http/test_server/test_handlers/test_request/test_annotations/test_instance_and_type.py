from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated

import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web
from rapidy.endpoint_handlers.attr_extractor import ParameterNotInstanceError
from rapidy.parameters.http import Body


async def annotated_def_handler(attr: Annotated[Any, Body()]) -> None:
    pass


async def default_def_handler(attr: Any = Body()) -> None:
    pass


async def annotated_def_handler_param_not_instance(attr: Annotated[Any, Body]) -> None:
    pass


async def default_def_handler_param_not_instance(attr: Any = Body) -> None:
    pass


@pytest.mark.parametrize(
    'handler',
    [
        pytest.param(annotated_def_handler, id='annotated-def'),
        pytest.param(default_def_handler, id='default-def'),
    ],
)
async def test_check_annotation(
    aiohttp_client: AiohttpClient,
    handler: Any,
) -> None:
    app = web.Application()
    app.add_routes([web.post('/', handler)])
    client = await aiohttp_client(app)
    resp = await client.post('/', json={'attr': ''})

    assert resp.status == HTTPStatus.OK


@pytest.mark.parametrize(
    'handler',
    [
        pytest.param(annotated_def_handler_param_not_instance, id='annotated-def'),
        pytest.param(default_def_handler_param_not_instance, id='default-def'),
    ],
)
def test_annotation_must_be_instance(handler: Any) -> None:
    app = web.Application()
    with pytest.raises(ParameterNotInstanceError):
        app.add_routes([web.post('/', handler)])
