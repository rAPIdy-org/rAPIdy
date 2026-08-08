from __future__ import annotations

from http import HTTPStatus

from rapidy_core.constants import DEFAULT_JSON_ENCODER
from rapidy_core.enums import Charset, ContentType

from rapidy import Rapidy
from rapidy.routing import RouteRecord
from rapidy.routing.http.routers import get, post


async def handler_a() -> str:
    return 'a'


async def handler_b() -> str:
    return 'b'


async def handler_c() -> str:
    return 'c'


route_a = get('/a', status_code=201, response_content_type=ContentType.json)(handler_a)
route_b = post('/b')(handler_b)
route_c = get.reg('/c', handler_c)


def test_public_route_registry_contains_openapi_ready_metadata() -> None:
    app = Rapidy(http_route_handlers=[route_a, route_b, route_c])
    records = app.routes

    assert all(isinstance(record, RouteRecord) for record in records)
    assert [(record.path, record.method) for record in records] == [
        ('/a', 'GET'),
        ('/a', 'HEAD'),
        ('/b', 'POST'),
        ('/c', 'GET'),
        ('/c', 'HEAD'),
    ]
    assert all('allow_head' not in record.route_kwargs for record in records)

    record_a = records[0]
    assert record_a.handler is handler_a
    assert record_a.allow_head is True
    assert record_a.is_auto_head is False
    assert record_a.route_kwargs['status_code'] == 201
    assert record_a.route_kwargs['response_content_type'] is ContentType.json

    auto_head_a = records[1]
    assert auto_head_a.handler is handler_a
    assert auto_head_a.is_auto_head is True

    record_b = records[2]
    assert record_b.handler is handler_b
    assert record_b.route_kwargs['status_code'] == HTTPStatus.OK
    assert record_b.route_kwargs['response_validate'] is True
    assert record_b.route_kwargs['response_charset'] is Charset.utf8
    assert record_b.route_kwargs['response_content_type'] is None
    assert record_b.route_kwargs['response_by_alias'] is True
    assert record_b.route_kwargs['response_exclude_unset'] is False
    assert record_b.route_kwargs['response_exclude_defaults'] is False
    assert record_b.route_kwargs['response_exclude_none'] is False
    assert record_b.route_kwargs['response_json_encoder'] is DEFAULT_JSON_ENCODER

    record_c = records[3]
    assert record_c.handler is handler_c
    assert record_c.allow_head is True
