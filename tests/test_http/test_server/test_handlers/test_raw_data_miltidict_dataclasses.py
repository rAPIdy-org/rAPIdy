from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Dict, Type

import pytest
from aiohttp.pytest_plugin import AiohttpClient

from rapidy import web


@dataclass
class TestCase:
    id: str

    param: Type[Any]
    request_kw: Dict[str, Any] = field(default_factory=dict)
    endpoint_path: str = '/'
    request_path: str = '/'

    __test__ = False


test_cases = (
    TestCase(
        id='PathParams',
        param=web.PathParams,
        endpoint_path='/{test}',
        request_path='/test',
    ),
    TestCase(
        id='Headers',
        param=web.Headers,
        request_kw={'headers': {'test': 'test'}},
    ),
    TestCase(
        id='Cookies',
        param=web.Cookies,
        request_kw={'cookies': {'test': 'test'}},
    ),
    TestCase(
        id='QueryParams',
        param=web.QueryParams,
        request_kw={'params': {'test': 'test'}},
    ),
)


@dataclass
class Data:
    test: str


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
async def test_success(aiohttp_client: AiohttpClient, *, test_case: TestCase) -> None:
    async def handler(data: Data = test_case.param()) -> None:
        pass

    app = web.Application()
    app.add_routes([web.post(test_case.endpoint_path, handler)])

    client = await aiohttp_client(app)
    resp = await client.post(test_case.request_path, **test_case.request_kw)

    assert resp.status == HTTPStatus.OK
