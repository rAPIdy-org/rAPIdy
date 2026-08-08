from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

import pytest

from rapidy import Rapidy
from rapidy.http import Cookies, Headers, PathParams, post, QueryParams
from tests.ported.client import AppClientFactory


@dataclass
class TestCase:
    id: str

    param: type[Any]
    request_kw: dict[str, Any] = field(default_factory=dict)
    endpoint_path: str = '/'
    request_path: str = '/'

    __test__ = False


test_cases = (
    TestCase(
        id='PathParams',
        param=PathParams,
        endpoint_path='/{test}',
        request_path='/test',
    ),
    TestCase(
        id='Headers',
        param=Headers,
        request_kw={'headers': {'test': 'test'}},
    ),
    TestCase(
        id='Cookies',
        param=Cookies,
        request_kw={'cookies': {'test': 'test'}},
    ),
    TestCase(
        id='QueryParams',
        param=QueryParams,
        request_kw={'params': {'test': 'test'}},
    ),
)


@dataclass
class Data:
    test: str


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
async def test_success(app_client: AppClientFactory, *, test_case: TestCase) -> None:
    async def handler(data: Data = test_case.param()) -> None:
        pass

    app = Rapidy(http_route_handlers=[post.reg(test_case.endpoint_path, handler)])

    client = await app_client(app)
    resp = await client.post(test_case.request_path, **test_case.request_kw)

    assert resp.status == HTTPStatus.OK
