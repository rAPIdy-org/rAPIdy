from http import HTTPStatus
from typing import Any

import pytest
from pydantic import BaseModel
from rapidy_core.parameters.http import QueryParam, QueryParams

from rapidy import Rapidy
from rapidy.http import post, Response
from tests.ported.client import AppClientFactory


class SchemaA(BaseModel):
    a: int


class SchemaB(BaseModel):
    b: int


@pytest.mark.parametrize(
    'annotation, param_type, params, expected_type',
    (
        (int | str, QueryParam, {'p': 1}, str),
        (int | str, QueryParam, {'p': '1'}, str),
        (int | str, QueryParam, {'p': '1s'}, str),
        (SchemaA | SchemaB, QueryParams, {'a': 1}, SchemaA),
        (SchemaA | SchemaB, QueryParams, {'b': 1}, SchemaB),
    ),
)
async def test_union_datatype(
    annotation: Any,
    param_type: Any,
    app_client: AppClientFactory,
    params: dict[str, Any],
    expected_type: type[Any],
) -> None:
    async def handler(p: annotation = param_type()) -> Response:
        assert isinstance(p, expected_type)
        return Response()

    app = Rapidy(http_route_handlers=[post.reg('/', handler)])

    client = await app_client(app)
    resp = await client.post('/', params=params)

    assert resp.status == HTTPStatus.OK
