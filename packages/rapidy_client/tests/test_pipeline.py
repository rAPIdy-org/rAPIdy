from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar, cast

import pytest
from rapidy_client import (
    UNSET,
    URL,
    CallNext,
    ContentFactory,
    Headers,
    Request,
    RequestExtensions,
    Response,
    ResponseExtensions,
    Timeout,
)
from rapidy_client._pipeline import DeclaredMiddlewaresSlot, build_pipeline


class _StubTransport:
    def __init__(self) -> None:
        self.received: list[Request] = []

    async def handle(self, request: Request) -> Response:
        self.received.append(request)
        return _make_response(request)

    async def aclose(self) -> None:
        return None


class _Spy:
    handshake_safe: ClassVar[bool] = False

    def __init__(
        self,
        label: str,
        log: list[str],
        *,
        reads: str | None = None,
        seen: list[Any] | None = None,
    ) -> None:
        self.label = label
        self.log = log
        self.reads = reads
        self.seen = seen

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        self.log.append(self.label)
        if self.reads is not None and self.seen is not None:
            self.seen.append(getattr(request.extensions, self.reads))
        return await call_next(request)


class _ReadContent:
    def __init__(self) -> None:
        self.seen: object = None

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        self.seen = request.content
        return await call_next(request)


class _ReplaceContent:
    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        request.content = b"replacement"
        return await call_next(request)


class _InspectRequest:
    def __init__(self) -> None:
        self.seen: tuple[object, ...] | None = None

    async def __call__(self, request: Request, call_next: CallNext) -> Response:
        self.seen = (
            request.method,
            request.url,
            request.headers,
            request.extensions,
            request.is_replayable,
        )
        request.headers = Headers({"X-Guard": "forwarded"})
        return await call_next(request)


class _NonReplayableBody:
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"body"


def _make_extensions(**overrides: Any) -> RequestExtensions:
    values: dict[str, Any] = {
        "upstream": "test",
        "endpoint": None,
        "request_id": None,
        "timeout": Timeout(),
        "retry": None,
        "idempotent": False,
        "auth_override": UNSET,
        "deadline": None,
        "redirects": cast(Any, None),
    }
    values.update(overrides)
    return RequestExtensions(**values)


def _make_request(*, content: Any = b"", **extensions: Any) -> Request:
    return Request(
        method="POST",
        url=URL("https://example.test/resource"),
        headers=Headers({"X-Test": "yes"}),
        content=content,
        extensions=_make_extensions(**extensions),
    )


def _make_response(request: Request) -> Response:
    return Response(
        status=200,
        headers=Headers(),
        request=request,
        extensions=ResponseExtensions(elapsed=0.0, attempt=1),
    )


@pytest.mark.asyncio
async def test_layer_order_2_5_outside_in() -> None:
    log: list[str] = []
    transport = _StubTransport()
    entry = build_pipeline(
        transport,
        correlation=_Spy("correlation", log),
        middlewares=(_Spy("user", log),),
        declared_slot=_Spy("declared", log),
        breaker=_Spy("breaker", log),
        rate_limit=_Spy("rate_limit", log),
        bulkhead=_Spy("bulkhead", log),
        retry=_Spy("retry", log),
        auth=_Spy("auth", log),
        per_attempt_middlewares=(_Spy("per_attempt", log),),
        trace_context=_Spy("trace_context", log),
        deadline=_Spy("deadline", log),
        timeout=_Spy("timeout", log),
        redirect=_Spy("redirect", log),
    )

    response = await entry(_make_request())

    assert response.status == 200
    assert log == [
        "correlation",
        "user",
        "declared",
        "breaker",
        "rate_limit",
        "bulkhead",
        "retry",
        "auth",
        "per_attempt",
        "trace_context",
        "deadline",
        "timeout",
        "redirect",
    ]
    assert len(transport.received) == 1


@pytest.mark.asyncio
async def test_order_2_5_v1_active_slots_only() -> None:
    log: list[str] = []
    transport = _StubTransport()
    entry = build_pipeline(
        transport,
        correlation=_Spy("correlation", log),
        declared_slot=_Spy("declared", log),
        retry=_Spy("retry", log),
        deadline=_Spy("deadline", log),
        timeout=_Spy("timeout", log),
        redirect=_Spy("redirect", log),
    )

    await entry(_make_request())

    assert log == [
        "correlation",
        "declared",
        "retry",
        "deadline",
        "timeout",
        "redirect",
    ]


@pytest.mark.asyncio
async def test_layer_order_pass_through_when_all_none() -> None:
    transport = _StubTransport()

    response = await build_pipeline(transport)(_make_request())

    assert response.status == 200
    assert len(transport.received) == 1


@pytest.mark.asyncio
async def test_pipeline_composition_is_fixed_at_build_time() -> None:
    log: list[str] = []
    configured = [_Spy("configured", log)]
    entry = build_pipeline(_StubTransport(), middlewares=configured)
    configured.append(_Spy("added-later", log))

    await entry(_make_request())

    assert log == ["configured"]


@pytest.mark.asyncio
async def test_extensions_override_reaches_stock_slot() -> None:
    seen: list[Any] = []
    entry = build_pipeline(
        _StubTransport(),
        middlewares=(_Spy("custom", [], reads="custom", seen=seen),),
    )

    await entry(_make_request(custom={"v": 1}))
    await entry(_make_request(custom={"v": 2}))

    assert seen == [{"v": 1}, {"v": 2}]


@pytest.mark.asyncio
async def test_extensions_override_retry_field_reaches_slot() -> None:
    seen: list[Any] = []
    override = object()
    entry = build_pipeline(
        _StubTransport(),
        middlewares=(_Spy("retry", [], reads="retry", seen=seen),),
    )

    await entry(_make_request(retry=None))
    await entry(_make_request(retry=override))

    assert seen == [None, override]


@pytest.mark.asyncio
async def test_declared_middlewares_slot_controller_then_method() -> None:
    log: list[str] = []
    request = _make_request(
        declared_middlewares=(
            _Spy("controller", log),
            _Spy("method", log),
        )
    )

    async def terminal(terminal_request: Request) -> Response:
        log.append("next")
        return _make_response(terminal_request)

    await DeclaredMiddlewaresSlot()(request, terminal)

    assert log == ["controller", "method", "next"]


@pytest.mark.asyncio
async def test_declared_middlewares_slot_empty_is_pass_through() -> None:
    log: list[str] = []
    request = _make_request(declared_middlewares=())

    async def terminal(terminal_request: Request) -> Response:
        log.append("next")
        return _make_response(terminal_request)

    await DeclaredMiddlewaresSlot()(request, terminal)

    assert log == ["next"]
    assert DeclaredMiddlewaresSlot.handshake_safe is False


@pytest.mark.asyncio
async def test_declared_slot_does_not_rebuild_chain() -> None:
    log: list[str] = []
    entry = build_pipeline(
        _StubTransport(),
        correlation=_Spy("correlation", log),
    )

    await entry(_make_request(declared_middlewares=(_Spy("first-request", log),)))
    await entry(
        _make_request(
            declared_middlewares=(
                _Spy("second-controller", log),
                _Spy("second-method", log),
            )
        )
    )

    assert log == [
        "correlation",
        "first-request",
        "correlation",
        "second-controller",
        "second-method",
    ]


@pytest.mark.asyncio
async def test_non_replayable_guard_raises_in_debug() -> None:
    middleware = _ReadContent()
    entry = build_pipeline(
        _StubTransport(),
        middlewares=(middleware,),
        debug=True,
    )

    with pytest.raises(RuntimeError, match="is_replayable=False"):
        await entry(_make_request(content=_NonReplayableBody()))


@pytest.mark.asyncio
async def test_non_replayable_guard_blocks_content_assignment_in_debug() -> None:
    entry = build_pipeline(
        _StubTransport(),
        middlewares=(_ReplaceContent(),),
        debug=True,
    )

    with pytest.raises(RuntimeError, match="is_replayable=False"):
        await entry(_make_request(content=_NonReplayableBody()))


@pytest.mark.asyncio
async def test_non_replayable_opaque_without_debug() -> None:
    body = _NonReplayableBody()
    middleware = _ReadContent()
    transport = _StubTransport()
    entry = build_pipeline(
        transport,
        middlewares=(middleware,),
        debug=False,
    )

    response = await entry(_make_request(content=body))

    assert response.status == 200
    assert middleware.seen is body
    assert transport.received[0].content is body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [b"body", ContentFactory(lambda: b"body")],
)
async def test_replayable_content_accessible_in_debug(body: object) -> None:
    middleware = _ReadContent()
    entry = build_pipeline(
        _StubTransport(),
        middlewares=(middleware,),
        debug=True,
    )

    response = await entry(_make_request(content=body))

    assert response.status == 200
    assert middleware.seen is body


@pytest.mark.asyncio
async def test_guarded_request_forwards_url_headers_extensions() -> None:
    middleware = _InspectRequest()
    transport = _StubTransport()
    request = _make_request(content=_NonReplayableBody())
    original_headers = request.headers
    entry = build_pipeline(
        transport,
        middlewares=(middleware,),
        debug=True,
    )

    await entry(request)

    assert middleware.seen == (
        "POST",
        request.url,
        original_headers,
        request.extensions,
        False,
    )
    assert transport.received[0].headers.get("X-Guard") == "forwarded"


@pytest.mark.asyncio
async def test_transport_receives_raw_request_under_debug() -> None:
    transport = _StubTransport()
    body = _NonReplayableBody()
    request = _make_request(content=body)

    await build_pipeline(transport, debug=True)(request)

    assert transport.received == [request]
    assert type(transport.received[0]) is Request
    assert transport.received[0].content is body


@pytest.mark.asyncio
async def test_retry_none_single_attempt() -> None:
    log: list[str] = []
    transport = _StubTransport()
    entry = build_pipeline(
        transport,
        retry=None,
        deadline=_Spy("deadline", log),
        timeout=_Spy("timeout", log),
        redirect=_Spy("redirect", log),
    )

    await entry(_make_request(retry=None))

    assert log == ["deadline", "timeout", "redirect"]
    assert len(transport.received) == 1
