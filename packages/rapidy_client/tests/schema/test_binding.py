from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

import pytest
import rapidy_client
from pydantic import BaseModel
from rapidy_client import (
    HttpClient,
    Request,
    Response,
    SchemaDefinitionError,
    UpstreamConfig,
    bind,
    operation,
)
from rapidy_client.schema import (
    Body,
    CallOptions,
    Cookie,
    File,
    Form,
    Header,
    ListStyle,
    PathParam,
    QueryParam,
    QuerySerialization,
    Stream,
    controller,
    delete,
    get,
    head,
    options,
    patch,
    post,
    put,
)
from rapidy_client.testing import MockTransport
from rapidy_core.parameters.http import PathParam as CorePathParam


def _client(mock: MockTransport) -> HttpClient:
    return HttpClient(
        UpstreamConfig(base_url="https://schema.example.test"), transport=mock
    )


def test_schema_facade_and_root_collision_contract() -> None:
    assert PathParam is CorePathParam
    assert ListStyle.REPEAT.value == "repeat"
    assert QuerySerialization().list_style is ListStyle.REPEAT
    assert Form().content_type == "application/x-www-form-urlencoded"
    assert File().content_type == "multipart/form-data"
    assert "PathParam" not in rapidy_client.__all__
    assert rapidy_client.Headers.__module__ == "rapidy_client._models"


@pytest.mark.parametrize(
    ("decorator", "method"),
    [
        (get, "GET"),
        (post, "POST"),
        (put, "PUT"),
        (patch, "PATCH"),
        (delete, "DELETE"),
        (head, "HEAD"),
        (options, "OPTIONS"),
    ],
)
def test_all_method_decorators(decorator: Callable[..., Any], method: str) -> None:
    async def declaration() -> None:
        raise NotImplementedError

    endpoint = decorator("/x")(declaration)

    assert endpoint.declaration.http_method == method


@pytest.mark.asyncio
async def test_marker_forms_produce_equivalent_requests() -> None:
    @get("/users/{user_id}")
    async def default_form(
        user_id: str = PathParam(),
        verbose: bool = QueryParam(alias="full"),
        trace: str = Header(alias="x-trace"),
    ) -> Response:
        raise NotImplementedError

    @get("/users/{user_id}")
    async def annotated_form(
        user_id: Annotated[str, PathParam()],
        verbose: Annotated[bool, QueryParam(alias="full")],
        trace: Annotated[str, Header(alias="x-trace")],
    ) -> Response:
        raise NotImplementedError

    first_mock = MockTransport()
    first_mock.route("GET", "/users/42").respond()
    second_mock = MockTransport()
    second_mock.route("GET", "/users/42").respond()

    await bind(default_form, _client(first_mock))(
        user_id="42", verbose=True, trace="abc"
    )
    await bind(annotated_form, _client(second_mock))(
        user_id="42", verbose=True, trace="abc"
    )

    first = first_mock.calls[0].request
    second = second_mock.calls[0].request
    assert first.method == second.method == "GET"
    assert str(first.url) == str(second.url)
    assert first.headers.multi_items() == second.headers.multi_items()


class _TraceMiddleware:
    def __init__(self, name: str, log: list[str]) -> None:
        self.name = name
        self.log = log

    async def __call__(self, request: Request, call_next: Any) -> Response:
        self.log.append(f"{self.name}:in")
        response = await call_next(request)
        self.log.append(f"{self.name}:out")
        return response


@pytest.mark.asyncio
async def test_controller_inheritance_middlewares_and_call_options() -> None:
    log: list[str] = []
    outer = _TraceMiddleware("controller", log)
    inner = _TraceMiddleware("method", log)

    @controller("/api", timeout=5.0, middlewares=(outer,))
    class Api:
        @get("/items/{item_id}", timeout=15.0, middlewares=(inner,), idempotent=False)
        async def item(self, item_id: str = PathParam()) -> Response:
            raise NotImplementedError

        @get("/ping")
        async def ping(self) -> Response:
            raise NotImplementedError

    mock = MockTransport()
    mock.route("GET", "/api/items/7").respond()
    mock.route("GET", "/api/ping").respond()
    api = bind(Api, _client(mock))

    await api.item("7", _options=CallOptions(timeout=30.0))
    await api.ping()

    item = mock.calls[0].request
    ping = mock.calls[1].request
    assert item.extensions.timeout.total == 30.0
    assert item.extensions.endpoint == "/api/items/{item_id}"
    assert item.extensions.idempotent is False
    assert item.extensions.declared_middlewares == (outer, inner)
    assert ping.extensions.timeout.total == 5.0
    assert ping.extensions.declared_middlewares == (outer,)
    assert log == [
        "controller:in",
        "method:in",
        "method:out",
        "controller:out",
        "controller:in",
        "controller:out",
    ]


@pytest.mark.asyncio
async def test_json_body_cookie_and_path_escape() -> None:
    @post("/users/{user_id}")
    async def update(
        user_id: Annotated[str, PathParam()],
        payload: Annotated[dict[str, object], Body()],
        session: Annotated[str, Cookie(alias="session")],
    ) -> Response:
        raise NotImplementedError

    mock = MockTransport()
    mock.route("POST", "/users/{first}/{second}").respond()

    await bind(update, _client(mock))(
        user_id="../admin", payload={"active": True}, session="token"
    )

    request = mock.calls[0].request
    assert "../admin" not in str(request.url)
    assert "%2E%2E%2F" in str(request.url)
    assert request.headers["cookie"] == "session=token"
    assert request.content == b'{"active": true}'


@pytest.mark.asyncio
async def test_bind_is_immutable_and_supports_two_clients() -> None:
    @get("/where")
    async def where() -> Response:
        raise NotImplementedError

    declaration = where.declaration
    first = MockTransport()
    first.route("GET", "/where").respond(status=201)
    second = MockTransport()
    second.route("GET", "/where").respond(status=202)

    first_bound = bind(where, _client(first))
    second_bound = bind(where, _client(second))
    first_response = await first_bound()
    second_response = await second_bound()

    assert first_response.status == 201
    assert second_response.status == 202
    assert where.declaration is declaration
    with pytest.raises(RuntimeError, match="bind"):
        where()


@pytest.mark.asyncio
async def test_stream_returns_context_manager_directly() -> None:
    @get("/download")
    async def download() -> Stream:
        raise NotImplementedError

    mock = MockTransport()
    mock.route("GET", "/download").respond(content=b"data")

    context = bind(download, _client(mock))()

    assert hasattr(context, "__aenter__")
    async with context as response:
        assert await response.aread() == b"data"


@pytest.mark.asyncio
async def test_operation_hides_and_injects_client() -> None:
    @operation
    async def confirm(
        client: HttpClient, invoice_id: str, *, force: bool = False
    ) -> int:
        response = await client.post(
            f"/invoices/{invoice_id}/confirm", query={"force": force}
        )
        return response.status

    mock = MockTransport()
    mock.route("POST", "/invoices/42/confirm").respond(status=204)
    bound = bind(confirm, _client(mock))

    assert tuple(inspect.signature(bound).parameters) == ("invoice_id", "force")
    assert await bound("42", force=True) == 204
    assert "force=true" in str(mock.calls[0].request.url)


def test_operation_rejects_method_form() -> None:
    with pytest.raises(SchemaDefinitionError, match="free function"):

        class Invalid:
            @operation
            async def execute(self) -> None:
                return None


class Invoice(BaseModel):
    invoice_id: int


class Conflict(BaseModel):
    message: str


def test_statuses_coverage_is_checked_at_bind() -> None:
    @get("/invoice", statuses={409: Conflict})
    async def invoice() -> Invoice:
        raise NotImplementedError

    with pytest.raises(SchemaDefinitionError, match="does not cover"):
        bind(invoice, _client(MockTransport()))


def test_statuses_covered_union_is_valid() -> None:
    @get("/invoice", statuses={404: None})
    async def invoice() -> Invoice | None:
        raise NotImplementedError

    bound: Callable[[], Awaitable[Invoice | None]] = bind(
        invoice, _client(MockTransport())
    )
    assert callable(bound)


def test_forward_reference_fails_at_bind_before_io() -> None:
    @get("/missing")
    async def missing(value: Annotated[MissingType, QueryParam()]) -> Response:  # type: ignore[name-defined]  # noqa: F821
        raise NotImplementedError

    mock = MockTransport()
    with pytest.raises(SchemaDefinitionError, match="missing"):
        bind(missing, _client(mock))
    assert not mock.calls
