from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated

import pytest
from rapidy_core.parameters.http import Body
from rapidy_core.signature import ParameterNotInstanceError

from rapidy import Rapidy
from rapidy.http import post
from tests.ported.client import AppClientFactory


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
    app_client: AppClientFactory,
    handler: Any,
) -> None:
    app = Rapidy(http_route_handlers=[post.reg('/', handler)])
    client = await app_client(app)
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
    with pytest.raises(ParameterNotInstanceError):
        Rapidy(http_route_handlers=[post.reg('/', handler)])
