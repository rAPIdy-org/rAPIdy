from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any
from typing_extensions import Annotated

import pytest
from pydantic import BaseModel
from rapidy_core.enums import ContentType
from rapidy_core.parameters.http import (
    Body,
    Cookie,
    Cookies,
    Header,
    Headers,
    PathParam,
    PathParams,
    QueryParam,
    QueryParams,
    RequestParamFieldInfo,
)

from rapidy import Rapidy
from rapidy.http import (
    controller,
    post as post_route,
    Request,
)
from rapidy.typedefs import View
from tests.ported.client import AppClientFactory


def _create_method_annotated_attr_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    async def post(attr: Annotated[validation_type, type_]) -> None:
        assert attr == expected_data

    return post


def _create_method_default_attr_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    async def post(attr: validation_type = type_) -> None:
        assert attr == expected_data

    return post


def _create_route_method_annotated_attr_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    @post_route('/{attr}')
    async def post(attr: Annotated[validation_type, type_]) -> None:
        assert attr == expected_data

    return post


def _create_route_method_default_attr_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    @post_route('/{attr}')
    async def post(attr: validation_type = type_) -> None:
        assert attr == expected_data

    return post


def _create_class_handler_as_annotated_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    class Foo(View):
        async def post(self, attr: Annotated[validation_type, type_]) -> None:
            assert attr == expected_data

    return Foo


def _create_class_handler_as_default_def(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    class Foo(View):
        async def post(self, attr: validation_type = type_) -> None:
            assert attr == expected_data

    return Foo


def _create_class_extended_handler_success(validation_type: Any, type_: Any, expected_data: Any) -> Any:
    class Foo(View):
        def __init__(self, request: Request) -> None:
            super().__init__(request)
            self.foo = 'foo'

        async def post(self, attr: validation_type = type_) -> None:
            assert self.foo
            assert attr == expected_data

    return Foo


class Schema(BaseModel):
    attr: str


@dataclass
class TestCase:
    id: str

    annotation: Any
    type_: RequestParamFieldInfo
    expected_data: Any
    request_kw: dict[str, Any] = field(default_factory=dict)

    __test__ = False


header_request_kw = {'headers': {'attr': 'attr'}}
cookie_request_kw = {'cookies': {'attr': 'attr'}}
query_request_kw = {'params': {'attr': 'attr'}}
body_json_request_kw = {'json': {'attr': 'attr'}}
body_form_data_request_kw = {'data': {'attr': 'attr'}}
multipart_body_request_kw = {
    'files': {'attr': (None, 'attr')},
}

expected_param_data: str = 'attr'
expected_extract_schema: Schema = Schema(attr='attr')
expected_extract_raw: dict[str, Any] = {'attr': 'attr'}

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
        annotation=dict[str, Any],
        type_=Cookies(validate=False),
        request_kw=cookie_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='query-raw',
        annotation=dict[str, Any],
        type_=QueryParams(validate=False),
        request_kw=query_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='body-json-raw',
        annotation=dict[str, Any],
        type_=Body(validate=False),
        request_kw=body_json_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='body-form-data-raw',
        annotation=dict[str, Any],
        type_=Body(validate=False, content_type=ContentType.x_www_form),
        request_kw=body_form_data_request_kw,
        expected_data=expected_extract_raw,
    ),
    TestCase(
        id='multipart-body-raw',
        annotation=dict[str, Any],
        type_=Body(validate=False, content_type=ContentType.m_part_form_data, check_content_type=False),
        request_kw=multipart_body_request_kw,
        expected_data=expected_extract_raw,
    ),
)

create_method_parameters = [
    pytest.param(_create_method_annotated_attr_def, id='attr-definition-as-annotated'),
    pytest.param(_create_method_default_attr_def, id='attr-definition-as-default'),
]
create_method_as_decorated_route_func_parameters = [
    pytest.param(_create_route_method_annotated_attr_def, id='attr-definition-as-annotated'),
    pytest.param(_create_route_method_annotated_attr_def, id='attr-definition-as-default'),
]
create_view_parameters = [
    pytest.param(_create_class_handler_as_annotated_def, id='attr-definition-as-annotated'),
    pytest.param(_create_class_handler_as_default_def, id='attr-definition-as-default'),
    pytest.param(_create_class_extended_handler_success, id='extended-view'),
]


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_method_parameters)
async def test_success_func_def(app_client: AppClientFactory, test_case: TestCase, handler_creation_func: Any) -> None:
    handler = handler_creation_func(
        validation_type=test_case.annotation,
        type_=test_case.type_,
        expected_data=test_case.expected_data,
    )

    app = Rapidy(http_route_handlers=[post_route.reg('/{attr}', handler)])

    await _test(app_client=app_client, app=app, request_kw=test_case.request_kw)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_method_as_decorated_route_func_parameters)
async def test_success_func_def_with_routes_deco(
    app_client: AppClientFactory,
    test_case: TestCase,
    handler_creation_func: Any,
) -> None:
    route = handler_creation_func(test_case.annotation, test_case.type_, test_case.expected_data)
    app = Rapidy(http_route_handlers=[route])

    await _test(app_client=app_client, app=app, request_kw=test_case.request_kw)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_view_parameters)
async def test_success_class_def_as_view(
    app_client: AppClientFactory,
    test_case: TestCase,
    handler_creation_func: Any,
) -> None:
    handler = handler_creation_func(test_case.annotation, test_case.type_, test_case.expected_data)

    app = Rapidy(http_route_handlers=[controller.reg('/{attr}', handler)])

    await _test(app_client, app, test_case.request_kw)


@pytest.mark.parametrize('test_case', [pytest.param(test_case, id=test_case.id) for test_case in test_cases])
@pytest.mark.parametrize('handler_creation_func', create_view_parameters)
async def test_success_class_def_as_subapp(
    app_client: AppClientFactory,
    test_case: TestCase,
    handler_creation_func: Any,
) -> None:
    handler = handler_creation_func(test_case.annotation, test_case.type_, test_case.expected_data)

    app = Rapidy(http_route_handlers=[controller.reg('/{attr}', handler)])

    sup_app = Rapidy(http_route_handlers=[controller.reg('/{attr}', handler)])

    app.add_subapp('/v1', sup_app)

    await _test(app_client, app, test_case.request_kw)
    await _test(app_client, app, test_case.request_kw, base_path='/v1/')


async def _test(
    app_client: AppClientFactory,
    app: Rapidy,
    request_kw: dict[str, Any] = {},
    base_path: str = '/',
) -> None:
    client = await app_client(app)
    resp = await client.post(base_path + 'attr', **request_kw)
    assert resp.status == HTTPStatus.OK
