from typing import Any

import pytest

from rapidy import web
from rapidy._request_handlers import AnotherDataExtractionTypeAlreadyExistsError
from tests.helpers import body_params, type_tuple_params


@pytest.mark.parametrize('type_tuple', type_tuple_params)
async def test_check_single_and_complex_params(type_tuple: Any) -> None:
    type1, type2 = type_tuple

    async def handler1(p1: Any = type1, p2: Any = type2) -> Any:
        return web.Response()

    async def handler2(p1: Any = type2, p2: Any = type1) -> Any:
        return web.Response()

    app = web.Application()

    with pytest.raises(AnotherDataExtractionTypeAlreadyExistsError):
        app.add_routes([web.post('/', handler1)])

    with pytest.raises(AnotherDataExtractionTypeAlreadyExistsError):
        app.add_routes([web.post('/', handler2)])


@pytest.mark.parametrize('type1', body_params)
@pytest.mark.parametrize('type2', body_params)
async def test_body_diff_types(type1: Any, type2: Any) -> None:
    if type1.__class__.__name__ == type2.__class__.__name__:
        return

    async def handler(p1: Any = type1, p2: Any = type2) -> Any:
        return web.Response()

    app = web.Application()
    with pytest.raises(AnotherDataExtractionTypeAlreadyExistsError):
        app.add_routes([web.post('/', handler)])
