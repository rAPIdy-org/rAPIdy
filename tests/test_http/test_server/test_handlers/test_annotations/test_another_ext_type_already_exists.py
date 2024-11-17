from typing import Any

import pytest

from rapidy import web
from rapidy.endpoint_handlers.http.request.data_validators import AnotherDataExtractionTypeAlreadyExistsError
from rapidy.enums import ContentType
from rapidy.parameters.http import (
    Body,
    Cookie,
    Cookies,
    Header,
    Headers,
    PathParam,
    PathParams,
    QueryParam,
    QueryParams,
)

type_tuple_params = (
    (PathParam(), PathParams()),
    (Header(), Headers()),
    (Cookie(), Cookies()),
    (QueryParam(), QueryParams()),
    (Body(body_type=ContentType.json), Body(body_type=ContentType.x_www_form)),
)

body_params = (
    Body(body_type=ContentType.json),
    Body(body_type=ContentType.x_www_form),
    Body(body_type=ContentType.m_part_form_data),
    Body(body_type=ContentType.stream),
    Body(body_type=ContentType.text_plain),
)


@pytest.mark.parametrize('type_tuple', type_tuple_params)
async def test_check_single_and_complex_params(type_tuple: Any) -> None:
    type1, type2 = type_tuple

    async def handler1(_: Any = type1, __: Any = type2) -> None: pass

    async def handler2(_: Any = type2, __: Any = type1) -> None: pass

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

    async def handler(_: Any = type1, __: Any = type2) -> None: pass

    app = web.Application()
    with pytest.raises(AnotherDataExtractionTypeAlreadyExistsError):
        app.add_routes([web.post('/', handler)])
