from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from enum import Enum
from typing import Annotated, Any
from urllib.parse import urlencode
from uuid import UUID

import pytest
from pydantic import BaseModel, Field
from rapidy_client import (
    ContentFactory,
    FilePart,
    HttpClient,
    Response,
    SchemaDefinitionError,
    UpstreamConfig,
    bind,
)
from rapidy_client.schema import (
    Body,
    Cookies,
    File,
    Form,
    Header,
    Headers,
    ListStyle,
    PathParams,
    QueryParams,
    QuerySerialization,
    controller,
    get,
    post,
)
from rapidy_client.schema._serialize import (
    expand_param_model,
    resolve_content_type,
    serialize_body,
    serialize_cookies,
    serialize_headers,
    serialize_query,
)
from rapidy_client.testing import MockTransport


class Color(Enum):
    RED = "red"
    NUMBER = 2


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"flag": True, "disabled": False}, [("flag", "true"), ("disabled", "false")]),
        (
            {"color": Color.RED, "number": Color.NUMBER},
            [("color", "red"), ("number", "2")],
        ),
        ({"day": date(2026, 8, 8)}, [("day", "2026-08-08")]),
        ({"skip": None, "keep": 1}, [("keep", "1")]),
        ({"empty": [], "none": [None]}, []),
        (
            {"integer": 3, "float": 1.5, "text": "x"},
            [("integer", "3"), ("float", "1.5"), ("text", "x")],
        ),
    ],
)
def test_query_scalar_defaults(
    values: dict[str, Any], expected: list[tuple[str, str]]
) -> None:
    assert serialize_query(values) == expected


def test_query_repeat_and_csv_list_style() -> None:
    values = {"tag": ["a", "b"]}

    assert serialize_query(values) == [("tag", "a"), ("tag", "b")]
    assert serialize_query(values, list_style=ListStyle.CSV) == [("tag", "a,b")]


def test_query_datetime_uuid_and_escape_boundary() -> None:
    identifier = UUID("c6819dc7-499f-4dd9-a12f-8f99c16a1d66")
    naive = datetime(2026, 8, 8, 12, 0)  # noqa: DTZ001 - naive is the subject
    aware = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)

    pairs = serialize_query(
        {"naive": naive, "aware": aware, "id": identifier, "q": "a b/../x"}
    )

    assert pairs[:3] == [
        ("naive", "2026-08-08T12:00:00+00:00"),
        ("aware", "2026-08-08T12:00:00+00:00"),
        ("id", str(identifier)),
    ]
    assert pairs[-1] == ("q", "a b/../x")
    assert "q=a+b%2F..%2Fx" in urlencode(pairs)


class Aggregate(BaseModel):
    internal: str = Field(alias="wire")
    optional: str | None = None


def test_header_cookie_and_aggregate_serialization() -> None:
    aggregate = Aggregate(wire="value")

    assert expand_param_model(aggregate) == {"wire": "value"}
    assert serialize_headers({"X-Count": 2, "X-On": True, "X-Skip": None}) == [
        ("X-Count", "2"),
        ("X-On", "true"),
    ]
    assert serialize_cookies({"sid": "abc", "theme": "dark", "skip": None}) == (
        "sid=abc; theme=dark"
    )


class Payload(BaseModel):
    identifier: int = Field(alias="id")
    name: str | None = None
    enabled: bool = True


def test_request_flags_serialize_json_body() -> None:
    payload = Payload(id=7)

    default_body = json.loads(serialize_body(payload, content_type="application/json"))
    filtered_body = json.loads(
        serialize_body(
            payload,
            content_type="application/json",
            request_exclude_none=True,
            request_exclude_defaults=True,
        )
    )
    named_body = json.loads(
        serialize_body(
            payload,
            content_type="application/json",
            request_by_alias=False,
            request_include_fields={"identifier"},
        )
    )

    assert default_body == {"id": 7, "name": None, "enabled": True}
    assert filtered_body == {"id": 7}
    assert named_body == {"identifier": 7}


def test_request_custom_and_json_encoder_are_used() -> None:
    class Token:
        pass

    calls: list[object] = []

    def encoder(value: object) -> str:
        calls.append(value)
        return json.dumps(value)

    body = serialize_body(
        {"token": Token()},
        content_type="application/json",
        request_custom_encoder={Token: lambda _: "encoded"},
        request_json_encoder=encoder,
    )

    assert json.loads(body) == {"token": "encoded"}
    assert calls == [{"token": "encoded"}]


def test_content_type_priority_and_raw_body() -> None:
    assert resolve_content_type() == "application/json"
    assert resolve_content_type(request_content_type="text/plain") == "text/plain"
    assert (
        resolve_content_type(
            body_marker_content_type="text/csv",
            request_content_type="application/json",
        )
        == "text/csv"
    )
    assert serialize_body(b"a,b\n", content_type="text/csv") == b"a,b\n"
    assert serialize_body("привет", content_type="text/plain").decode() == "привет"
    with pytest.raises(SchemaDefinitionError, match="must be bytes"):
        serialize_body({"x": 1}, content_type="text/csv")


class QueryAggregate(BaseModel):
    tags: list[str] = Field(alias="tag")
    omitted: str | None = None


class HeaderAggregate(BaseModel):
    trace: str = Field(alias="x-trace")


class CookieAggregate(BaseModel):
    session: str = Field(alias="sid")


class Invoice(BaseModel):
    invoice_id: int = Field(alias="id")


class InvoicePath(BaseModel):
    invoice_id: str


def _client(mock: MockTransport) -> HttpClient:
    return HttpClient(
        UpstreamConfig(base_url="https://serialize.example.test"), transport=mock
    )


@pytest.mark.asyncio
async def test_binding_serializes_aggregates_query_style_and_parses_model() -> None:
    @get("/invoices", query_serialization=QuerySerialization(list_style=ListStyle.CSV))
    async def list_invoices(
        query: Annotated[QueryAggregate, QueryParams()],
        headers: Annotated[HeaderAggregate, Headers()],
        cookies: Annotated[CookieAggregate, Cookies()],
        scalar: Annotated[bool, Header(alias="x-enabled")],
    ) -> Invoice:
        raise NotImplementedError

    mock = MockTransport()
    mock.route("GET", "/invoices").respond(json={"id": 7})

    result = await bind(list_invoices, _client(mock))(
        QueryAggregate(tag=["a", "b"]),
        HeaderAggregate(**{"x-trace": "trace-1"}),
        CookieAggregate(sid="session-1"),
        True,
    )

    request = mock.calls[0].request
    assert result == Invoice(id=7)
    assert request.url.query_string == "tag=a,b"
    assert request.headers["x-trace"] == "trace-1"
    assert request.headers["x-enabled"] == "true"
    assert request.headers["cookie"] == "sid=session-1"


@pytest.mark.asyncio
async def test_binding_applies_request_options_before_transport() -> None:
    @post("/invoices", request_exclude_none=True, request_exclude_defaults=True)
    async def create(payload: Annotated[Payload, Body()]) -> Invoice:
        raise NotImplementedError

    mock = MockTransport()
    mock.route("POST", "/invoices").respond(json={"id": 8})

    result = await bind(create, _client(mock))(Payload(id=8))

    request = mock.calls[0].request
    assert result == Invoice(id=8)
    assert request.content == b'{"id": 8}'
    assert request.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_path_aggregate_and_controller_request_options() -> None:
    @controller("/api", request_exclude_none=True)
    class Api:
        @post("/invoices/{invoice_id}", request_exclude_defaults=True)
        async def update(
            self,
            path: Annotated[InvoicePath, PathParams()],
            payload: Annotated[Payload, Body()],
        ) -> Response:
            raise NotImplementedError

    mock = MockTransport()
    mock.route("POST", "/api/invoices/7").respond()

    await bind(Api, _client(mock)).update(InvoicePath(invoice_id="7"), Payload(id=7))

    request = mock.calls[0].request
    assert request.content == b'{"id": 7}'


@pytest.mark.asyncio
async def test_body_content_type_wins_in_bound_request() -> None:
    @post("/csv", request_content_type="application/json")
    async def send_csv(
        payload: Annotated[str, Body(content_type="text/csv")],
    ) -> Response:
        raise NotImplementedError

    mock = MockTransport()
    mock.route("POST", "/csv").respond()

    await bind(send_csv, _client(mock))("a,b\n")

    request = mock.calls[0].request
    assert request.content == b"a,b\n"
    assert request.headers["content-type"] == "text/csv"


@pytest.mark.asyncio
async def test_form_and_file_execute_as_multipart() -> None:
    @post("/upload")
    async def upload(
        title: Annotated[str, Form()],
        content: Annotated[FilePart, File()],
    ) -> Response:
        raise NotImplementedError

    mock = MockTransport()
    mock.route("POST", "/upload").respond()
    await bind(upload, _client(mock))(
        "title",
        FilePart(name="ignored", content=b"content"),
    )

    request = mock.calls[0].request
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert isinstance(request.content, ContentFactory)
    body = b"".join([chunk async for chunk in request.content.open()])
    assert b'name="title"' in body
    assert b'name="content"' in body


@pytest.mark.asyncio
async def test_form_fields_execute_as_urlencoded() -> None:
    @post("/form")
    async def submit(
        title: Annotated[str, Form()],
        active: Annotated[bool, Form()],
    ) -> Response:
        raise NotImplementedError

    mock = MockTransport()
    mock.route("POST", "/form").respond()

    await bind(submit, _client(mock))("report", True)

    request = mock.calls[0].request
    assert request.content == b"active=true&title=report"
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"


@pytest.mark.asyncio
async def test_raw_stream_body_executes_declaratively() -> None:
    @post("/raw")
    async def upload(
        payload: Annotated[
            AsyncIterator[bytes], Body(content_type="application/octet-stream")
        ],
    ) -> Response:
        raise NotImplementedError

    async def chunks() -> AsyncIterator[bytes]:
        yield b"payload"

    mock = MockTransport()
    mock.route("POST", "/raw").respond()
    source = chunks()

    await bind(upload, _client(mock))(source)

    request = mock.calls[0].request
    assert request.content is source
    assert request.extensions.retry is None
    await source.aclose()
