from __future__ import annotations

from pydantic import BaseModel
from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.enums import Charset, ContentType

from rapidy import Rapidy
from rapidy.endpoint_handlers.http.attrs_extractor import get_http_handler_info
from rapidy.http import controller, get
from rapidy.typedefs import Unset


class Item(BaseModel):
    value: int


class OtherItem(BaseModel):
    label: str


RESPONSE_KEYS = {
    'status_code',
    'response_validate',
    'response_type',
    'response_content_type',
    'response_charset',
    'response_zlib_executor',
    'response_zlib_executor_size',
    'response_include_fields',
    'response_exclude_fields',
    'response_by_alias',
    'response_exclude_unset',
    'response_exclude_defaults',
    'response_exclude_none',
    'response_custom_encoder',
    'response_json_encoder',
}


def test_route_response_metadata_is_public_and_complete() -> None:
    @get(
        '/x',
        status_code=201,
        response_content_type=ContentType.json,
        response_exclude_none=True,
    )
    async def handler() -> Item:
        return Item(value=1)

    app = Rapidy(http_route_handlers=[handler])
    route = next(record for record in app.routes if record.path == '/x' and record.method == 'GET')
    assert route.route_kwargs.keys() >= RESPONSE_KEYS
    assert route.route_kwargs['status_code'] == 201
    assert route.route_kwargs['response_validate'] is True
    assert route.route_kwargs['response_type'] is Unset
    assert route.route_kwargs['response_content_type'] is ContentType.json
    assert route.route_kwargs['response_charset'] is Charset.utf8
    assert route.route_kwargs['response_exclude_none'] is True
    assert route.route_kwargs['response_json_encoder'] is DEFAULT_JSON_ENCODER
    assert get_http_handler_info(
        route.handler,
        request_attr_can_declare_fst=True,
    ).return_annotation is Item


def test_controller_metadata_contains_effective_merged_kwargs() -> None:
    @controller('/controller', status_code=201, response_content_type=ContentType.json)
    class Endpoints:
        @get('/method', response_exclude_none=True)
        async def method(self) -> Item:
            return Item(value=1)

    app = Rapidy(http_route_handlers=[Endpoints])
    route = next(record for record in app.routes if record.path == '/controller/method' and record.method == 'GET')
    assert route.route_kwargs.keys() >= RESPONSE_KEYS
    assert route.route_kwargs['status_code'] == 201
    assert route.route_kwargs['response_content_type'] is ContentType.json
    assert route.route_kwargs['response_exclude_none'] is True
    assert get_http_handler_info(
        route.handler,
        request_attr_can_declare_fst=True,
    ).return_annotation is Item


def test_explicit_response_type_is_introspectable() -> None:
    @get('/typed', response_type=OtherItem)
    async def handler() -> Item:
        return Item(value=1)

    app = Rapidy(http_route_handlers=[handler])
    route = next(record for record in app.routes if record.path == '/typed' and record.method == 'GET')
    assert route.route_kwargs['response_type'] is OtherItem
    assert get_http_handler_info(
        route.handler,
        request_attr_can_declare_fst=True,
    ).return_annotation is Item
