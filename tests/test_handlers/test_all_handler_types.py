from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Dict

import pytest
from aiohttp import MultipartWriter
from pydantic import BaseModel
from pytest import param
from pytest_aiohttp.plugin import AiohttpClient
from typing_extensions import Annotated

from rapidy import web
from rapidy._request_param_field_info import ParamFieldInfo
from rapidy.enums import ContentType
from rapidy.request_parameters import (
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
from rapidy.web import Application
from rapidy.web_routedef import RouteTableDef
from tests.helpers import BOUNDARY, create_multipart_headers


def _create_method_annotated_attr_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    async def post(
            attr: Annotated[validation_type, type_],
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    return post


def _create_method_default_attr_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    async def post(
            attr: validation_type = type_,
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    return post


def _create_route_method_annotated_attr_def(validation_type: Any, type_: Any, expected_data: Any, routes: Any) -> Any:
    @routes.post('/{attr}')
    async def post(
            attr: Annotated[validation_type, type_],
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    return post


def _create_route_method_default_attr_def(validation_type: Any, type_: Any, expected_data: Any, routes: Any) -> Any:
    @routes.post('/{attr}')
    async def post(
            attr: validation_type = type_,
    ) -> web.Response:
        assert attr == expected_data
        return web.Response()

    return post


def _create_class_handler_as_annotated_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    class Foo(web.View):
        async def post(
                self,
                attr: Annotated[validation_type, type_],
        ) -> web.Response:
            assert attr == expected_data
            return web.Response()

    return Foo


def _create_class_handler_as_default_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    class Foo(web.View):
        async def post(
                self,
                attr: validation_type = type_,
        ) -> web.Response:
            assert attr == expected_data
            return web.Response()

    return Foo


def _create_class_extended_handler_success(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    class Foo(web.View):
        def __init__(self, request: web.Request) -> None:
            super().__init__(request)
            self.foo = 'foo'

        async def post(
                self,
                attr: validation_type = type_,
        ) -> web.Response:
            assert self.foo
            assert attr == expected_data
            return web.Response()

    return Foo



class Schema(BaseModel):
    attr: str


@dataclass
class TestCase:
    id: str

    annotation: Any
    type_: ParamFieldInfo
    expected_data: Any
    request_kw: Dict[str, Any] = field(default_factory=dict)

    __test__ = False


multipart_writer = MultipartWriter(boundary=BOUNDARY)
multipart_writer.append('attr', create_multipart_headers(part_name='attr'))


header_request_kw = {'headers': {'attr': 'attr'}}
cookie_request_kw = {'cookies': {'attr': 'attr'}}
query_request_kw = {'params': {'attr': 'attr'}}
body_json_request_kw = {'json': {'attr': 'attr'}}
body_form_data_request_kw = {'data': {'attr': 'attr'}}
multipart_body_request_kw = {
    'headers': {'content-type': f'multipart/form-data; boundary={BOUNDARY}'},
    'data': multipart_writer,
}

expected_param_data: str = 'attr'
expected_extract_schema: Schema = Schema(attr='attr')
expected_extract_raw: Dict[str, Any] = {'attr': 'attr'}

test_cases = (
    TestCase(
        id='path-param',
        annotation=str,
        type_=PathParam(),
        expected_data=expected_param_data,
    ),
    TestCase(
        id='header-param',
        annotation=str,
        type_=Header(),
        request_kw=header_request_kw,
        expected_data=expected_param_data,
    ),
    TestCase(
        id='cookie-param',
        annotation=str,
        type_=Cookie(),
        request_kw=cookie_request_kw,
        expected_data=expected_param_data,
    ),
    TestCase(
        id='query-param',
        annotation=str,
        type_=QueryParam(),
        request_kw=query_request_kw,
        expected_data=expected_param_data,
    ),
    TestCase(
        id='path-schema',
        annotation=Schema,
        type_=PathParams(),
        expected_data=expected_extract_schema,
    ),
    TestCase(
        id='header-schema',
        annotation=Schema,
        type_=Headers(),
        request_kw=header_request_kw,
        expected_data=expected_extract_schema,
    ),
    TestCase(
        id='cookie-schema',
        annotation=Schema,
        type_=Cookies(),
        request_kw=cookie_request_kw,
        expected_data=expected_extract_schema,
    ),
    TestCase(
        id='query-schema',
        annotation=Schema,
        type_=QueryParams(),
        request_kw=query_request_kw,
        expected_data=expected_extract_schema,
    ),
    TestCase(
        id='body-json',
        annotation=Schema,
        type_=Body(),
        request_kw=body_json_request_kw,
        expected_data=expected_extract_schema,
    ),
    TestCase(
        id='body-form',
        annotation=Schema,
        type_=Body(content_type=ContentType.x_www_form),
        request_kw=body_form_data_request_kw,
        expected_data=expected_extract_schema,
    ),
    TestCase(
        id='multipart-body',
        annotation=Schema,
        type_=Body(content_type=ContentType.m_part_form_data, check_content_type=False),
        request_kw=multipart_body_request_kw,
        expected_data=expected_extract_schema,
    ),
    TestCase(
        id='path-raw',
        annotation=Schema,
        type_=PathParams(validate=False),
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='cookie-raw',
        annotation=Dict[str, Any],
        type_=Cookies(validate=False),
        request_kw=cookie_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='query-raw',
        annotation=Dict[str, Any],
        type_=QueryParams(validate=False),
        request_kw=query_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='body-json-raw',
        annotation=Dict[str, Any],
        type_=Body(validate=False),
        request_kw=body_json_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='body-form-data-raw',
        annotation=Dict[str, Any],
        type_=Body(validate=False, content_type=ContentType.x_www_form),
        request_kw=body_form_data_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='multipart-body-raw',
        annotation=Dict[str, Any],
        type_=Body(validate=False, content_type=ContentType.m_part_form_data, check_content_type=False),
        request_kw=multipart_body_request_kw,
        expected_data=expected_extract_raw,
    ),
)

create_method_parameters = [
    param(_create_method_annotated_attr_def, id='attr-definition-as-annotated'),
    param(_create_method_default_attr_def, id='attr-definition-as-default'),
]
create_method_as_decorated_route_func_parameters = [
    param(_create_route_method_annotated_attr_def, id='attr-definition-as-annotated'),
    param(_create_route_method_annotated_attr_def, id='attr-definition-as-default'),
]
create_view_parameters = [
    param(_create_class_handler_as_annotated_def, id='attr-definition-as-annotated'),
    param(_create_class_handler_as_default_def, id='attr-definition-as-default'),
    param(_create_class_extended_handler_success, id='extended-view'),
]


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_method_parameters)
async def test_success_func_def(aiohttp_client: AiohttpClient, test_case: TestCase, handler_creation_func: Any) -> None:
    handler = handler_creation_func(
        validation_type=test_case.annotation, type_=test_case.type_, expected_data=test_case.expected_data,
    )

    app = Application()
    app.add_routes([web.post('/{attr}', handler)])

    await _test(aiohttp_client=aiohttp_client, app=app, request_kw=test_case.request_kw)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_method_as_decorated_route_func_parameters)
async def test_success_func_def_with_routes_deco(
        aiohttp_client: AiohttpClient, test_case: TestCase, handler_creation_func: Any,
) -> None:
    routes = RouteTableDef()

    handler_creation_func(test_case.annotation, test_case.type_, test_case.expected_data, routes=routes)

    app = Application()
    app.add_routes(routes)

    await _test(aiohttp_client=aiohttp_client, app=app, request_kw=test_case.request_kw)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_view_parameters)
async def test_success_class_def_as_view(
        aiohttp_client: AiohttpClient, test_case: TestCase, handler_creation_func: Any,
) -> None:
    handler = handler_creation_func(test_case.annotation, test_case.type_, test_case.expected_data)

    app = Application()
    app.add_routes([web.view('/{attr}', handler)])

    await _test(aiohttp_client, app, test_case.request_kw)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_view_parameters)
async def test_success_class_def_as_subapp(
        aiohttp_client: AiohttpClient, test_case: TestCase, handler_creation_func: Any,
) -> None:
    handler = handler_creation_func(test_case.annotation, test_case.type_, test_case.expected_data)

    app = Application()
    app.add_routes([web.post('/{attr}', handler)])

    sup_app = Application()
    sup_app.add_routes([web.post('/{attr}', handler)])

    app.add_subapp('/v1', sup_app)

    await _test(aiohttp_client, app, test_case.request_kw)
    await _test(aiohttp_client, app, test_case.request_kw, base_path='/v1/')


async def _test(
        aiohttp_client: AiohttpClient,
        app: web.Application,
        request_kw: Dict[str, Any] = {},
        base_path: str = '/',
) -> None:
    client = await aiohttp_client(app)
    resp = await client.post(base_path + 'attr', **request_kw)
    assert resp.status == HTTPStatus.OK
